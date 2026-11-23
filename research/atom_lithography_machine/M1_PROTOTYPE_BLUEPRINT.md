# `M1` Fiziksel Laboratuvar Prototipi Tasarım ve Kurulum Planı (`M1_PROTOTYPE_BLUEPRINT`)

**Sürüm:** v3.0 (Tam `v4.0` Gece Dalgası Kilitli — `Exp124–135`, `CAD v4.0`, `CellISA v3.0`, `BOED`, `BOM_DETAILED v4.0`, `7-RFQ` — 2026-11-23; v2.1: 2026-11-23; v1.0 taslak: 2026-11-22).  
**Dayanak:** [DESIGN.md](DESIGN.md) (`v4.0`), [MODULAR.md](MODULAR.md) (`v4.0-ICD`), [BOM_DETAILED.csv](BOM_DETAILED.csv) (`v4.0`), [BOM_ENGINEERING.md](BOM_ENGINEERING.md), [RFQ_SPECIFICATIONS.md](RFQ_SPECIFICATIONS.md) (`7-RFQ`), [LITERATURE.md](LITERATURE.md), [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md) (`v4.0`), `results/exp124..135*`.

> **Epistemik Sınır ve Amaç:** Bu belge, `M0` (teori/model/EDA) aşamasından ilk fiziksel laboratuvar gösterimine (**`M1` — tek-demet sayılmış implantasyon + `S5.5` ms flaş tavlama + `S6.9` `PT420` titreşim yalıtımı + `BOED` uyarlamalı spektroskopi + tek-yuva ölç–seç–kalibre–programla + `G6b` `ENDOR` Risk `R1` doğrulama kapısı**) geçişin eksiksiz mühendislik planıdır. **Projede henüz laboratuvar ölçümü, tedarikçi teklifi veya üretilmiş donanım yoktur (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).** `Exp124`–`Exp135` sayısal hedefleri ve dürüst `FAIL` sınırları (`Exp129 R1`, `Exp131 M4`, `Exp134 CX4`) aşağıda mühürlenmiştir.

---

## 1. `M1` Görev Tanımı, Bütçe Özeti ve Çıkış Ölçütü
- **Tek Cümlelik Hedef:** Seyreltik epitaksiyel `²⁹Si` banyosu (`f = %1,0`, Mod B — donör saçılmasından etkilenmeyen baz mod, `Exp124 CD8`) taşıyan bir `²⁸Si` test kuponu üzerinde, tek-demet `10→5 keV` sayılmış `³¹P⁺` implantasyonu + `100 K` soğuk-ada IBIC tek-iyon algılaması + **`S5.5` `808 nm / 1,0 ms` (`41,15 J/cm²`) flaş tavlama** (`Exp130`) + **`S6.9` ayrıştırılmış `PT420`** (`σ_stage = 0,1024 nm`, `Exp133`) + `MXC` (`~20 mK`, `1,500000 T`) **`BOED` uyarlamalı tek-donor ESR/ENDOR** (`41,03 ms`, `Exp132`) + yazmaç-özgü `XY8`-GRAPE senteziyle:
  1. **En az bir (hedef: `≥ 3`) sertifikalı `K=8` (veya evrensel `K=4` altküme) çekirdek-spin yazmacını fiziksel olarak doğrulamak ve `CellISA v3.0` üzerinden `Bell`/`GHZ-4`/`BitFlip-3`/`QFT-3` programlarını koşturmak** `[DESIGN.md §10 | M1]`,
  2. **`G6b` (`Exp129` Risk `R1`) deneysel `ENDOR` ölçümüyle `f = %1` gerçek çalışma veriminin `VOKL-6 HM5962 (%33,25)` ile `KL (%50,50)` arasında olduğunu (ve `VOKL-6 norm %4,75` kırmızı çizgisinin üstünde kaldığını) kanıtlayarak `M4` `N_cand*` kararını kilitlemek.**
- **Finansal ve Stratejik Mantık (`Exp128 v4.0` + `Exp134` / `BOM_ENGINEERING.md`):**
  - `M1 v4.0` nominal donanım maliyeti: **`$2.336.270`** (`$1.360.570–$4.210.190`; `M3 v4.0` `$4.609.600` toplamının **`%50,7`'si**; `v3.0`'dan `+$146.500` artış: `S5.5` flaş tavlama `+$66,5k`, `S6.9` `PT420` ayrıştırma `+$68,0k`, `S7.1-04` `BOED` GPU `+$12,0k`; `S6.10` `M4` cQED `$245k` `M4`'e ötelenir).
  - Tahmini program bedeli (`×3–×5,5–×10`): `$7,0M – $12,8M – $23,4M` (`$50M` yumuşak sınırın yarısının altında); `Exp134` **5 yıllık `M1` Lab TCO = `$8,62M`** (`M3` 5 yıllık Fab TCO = `$16,07M`).
  - **Yüksek Yatırım Koruması:** `M1` donanım bedelinin yaklaşık **`%83`'ü (`~$1,95M`)** (`20 mK` DR `$720k`, `PT420` + `S6.9` ayrıştırma, `8`-bobinli `1,50 T` mıknatıs `$185k`, UHV oda/pompalar, `S5.5` flaş tavlama optiği, `PH₃` gaz kabini/scrubber, `6-DOF` piezo, lazer interferometre, `HDA-HiRes` enerji süzgeci, `10→5 keV` kolon, `BOED` GPU) doğrudan `M3` altın ölçek makinesinin çekirdek gövdesine taşınır — **`M1` çöpe giden tek kullanımlık bir düzenek değil, modüler (`MODULAR.md v4.0-ICD`) yükseltilebilir ana platformdur.**
  - **Kaldırılan Birincil Riskler:** `M1`, `M3`'teki en ağır üç `R&D`/tedarik riskini (`S2.1–S2.3` çok-demet MEMS NRE `$661k`, `S6.6` `56`-zincir `B/C` duvarı `%73,4` varyans, `S6.10` `M4` `3 kΩ NbTiN` cQED `$245k`) ve SKY130 çip tape-out bağımlılığını (`R5/Exp123`) dışarıda bırakır.

---

## 2. `M3 v4.0` (Altın Ölçek) → `M1 v4.0` (Tek-Demet Prototip) Alt-Sistem İndirgeme Tablosu (`Exp128 v4.0` Kilitli)

| Alt Sistem | `M3 v4.0` Altın Ölçek (`$4.609.600` Nom) | `M1 v4.0` Tek-Demet Prototipi (`$2.336.270` Nom) | `M1` Payı | Kilitli Fizik / Mühendislik Şartnamesi (`Exp124–135`) |
|---|---|---|---:|---|
| **`S1` Kaynak & Kolon** | Çift hat (`³¹P⁺/²⁹Si⁺`), `$416.000` | **Tek hat (`³¹P⁺`, Mod B)** duoplazmatron + `PH₃` kabini/scrubber + Wien + `HDA-HiRes` + `10→5 keV` kolon (**`$319.750`**) | `%76,9` | Kolon `562,66 mm / Ø110 mm / 25,92 kg`; Wien `0,45 T, 150 mm, R_m=120,6`; **`HDA-HiRes`** (`R₀=40 mm, ΔE_FWHM=0,453 eV`); wafer `0 V`, üst gömlek `−5 kV`, anot `+5 kV` (`Exp124`) |
| **`S2` Yazma Kafası** | **`32×32 = 1.024` eş-adımlı `0,50 mm`** MEMS apertür/blanker/`Arch-B` (`16×16 mm < Ø28 mm`, `16×` 64-ch karo), `$775.500` | **Tek-delikli mikro-apertür + tek kanal blanker + tek eksenli `Arch-B` yavaşlatıcı lens** (**`$147.750`**) | `%19,1` | **`Arch-B`**: `WD = 0,250 mm`, `E_gap = 10,60 MV/m`, `C_c = 2,660 mm`, `C_s = 10,786 mm`, `σ_spot = 1,428–1,532 nm`; `Exp133` + `Exp135` birleşik **`σ_tot = 3,578 nm (10 ms) / 3,620 nm (15 ms)`** |
| **`S3` Soğuk-Ada IBIC Algılama** | `16×8` kanal vakum-içi CSA + çok-karolu FPGA, `$224.000` | **`1–2` adet 8-kanallı `100 K` soğuk-ada IBIC kartı (`src/board/`) + 1 adet FPGA kartı (`blanker_gate.v`)** (**`$88.550`**) | `%39,5` | **KRİTİK `Exp127` KİLİDİ:** RT `200 ns` `5 keV`'de `η=0,097` FAIL! **`100 K` soğuk adada `LTC6268` CSA (`Cf=0,25 pF, Rf=1 GΩ`) + `ADA4817-1` (`τ=1,2 µs, ×50`) + `DAC8568` + `TLV3501` (`204` parça, `0` ERC):** **`ENC = 24,1 e⁻`**, **`η(5 keV, 0,5 pF) = 0,99936`**, `C_det ≤ 1,5 pF`, `P_false = 2,59×10⁻⁴ / 1 ms` |
| **`S4` Konum & İnterferometri** | Granit + aktif tabla + `VC-E` (`VC-G` ops.) + `6-DOF` piezo + 3-eksen interferometre (`Zerodur + Invar-36`), `$253.000` | Aynı yalıtım & `6-DOF` UHV piezo + 2/3-eksen `pm` interferometre + `Zerodur/Invar-36` kaide (**`$233.920`**) | `%92,5` | **`Exp133` kilitli:** `43,57 Hz` PID (`PM = 55,23°, GM = 8,69 dB`) + `25 dB` harmonik FF → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**, **`σ_thermal = 0,0283 nm`** (`20 mK` termal kararlılık; çıplak `316LN` `1,935 nm` RED) |
| **`S5` UHV & `S5.5` Flaş Tavlama** | `s=0,5` UHV oda (`34,86 L`) + load-lock + **`S5.5` `808 nm / 1 ms` flaş tavlama (`$95k`)** + `25`-yonga epi lotu, `$338.000` | Aynı UHV oda/pompa + **`S5.5` `808 nm` flaş tavlama (tek-kupon kurulumu, `$66,5k`)** + `5`-yonga `f=%1,0` deneme epi lotu (**`$263.300`**) | `%77,9` | **`Exp130` (`R6` model-kapalı):** `+Y` CF63 AR safir (`Ø44 mm CA`, `T_AR=%98`, `9,47×` LIDT), **`808 nm / 1,0 ms / 1440,3 K`**, **`F = 41,15 J/cm² ± %5`** → **`f_act = %99,98`**, **`σ_anneal = 0,328 nm ≤ 0,50 nm`**, yüzey+vakum kaybı **`%0,022`**, `σ_iso = 0,0314 nm`, `10 µs` çift-renkli pirometre |
| **`S6` Kriyo, `S6.9` `PT420`, Mıknatıs & Okuma** | `20 mK` DR + `PT420` + **`S6.9` `PT420` ayrıştırma (`$68k`)** + `8`-bobin `1,5 T` + `56` zincir + **`S6.10` `M4` cQED (`$245k`)**, `$2.238.900` | **Aynı `20 mK` DR (`$720k`) + `PT420` + `S6.9` tam ayrıştırma (`$68k`, ZORUNLU!) + `8`-bobin `1,50 T` mıknatıs (`$185k`) + `2` okuma zinciri** (`S6.10` `M4`'e erteli) (**`$1.124.300`**) | `%50,2` | **`Exp133` ZORUNLU `S6.9` (`CFG4`):** rijit `PT420` `2.052 nm` çöker! `500 mm` uzak döner valf + `600 mm` esnek He + `k_bellows=2.000 N/m` 316L körük + `4×` S-halka OFHC Cu örgü (`k_braid=52,7 N/m`, `ΔT=3,7 mK`). **`Exp125`:** `1,500000 T ± 17,8 ppm`, `B_res=22,3 µT`, `T_quench=64,6 K` |
| **`S7–S8` Kontrol, `BOED` & `CellISA v3.0`** | `2×` GPU + **`S7.1-04` `BOED` hızlandırıcı (`$12k`)** + çok-şase AWG + SKY130 MPW, `$216.200` | `1×` GPU iş istasyonu + **`S7.1-04` `BOED` GPU (`$12k`)** + `1×` AWG + `1×` `ZCU216` + `1×` EMI kabin + **`machine_control` v3.0 (`BOED` + `CellISA v3.0`)** (**`$116.450`**) | `%53,9` | **`Exp132` (`$0` ek HW kipi):** `BOED` spektroskopiyi `1.000 ms →` **`41,03 ms`** (`24,37×` ham hızlanma, `RMS = 72,67 Hz`, `FNR = %0,20`, `FPR = %0,00`), `CellISA v3.0` (`14` komut) + SHA-256 sertifika |
| **`S9` Sarf & Yedek** | Tam yedek MEMS/LNA + 1 yıllık gaz, `$148.000` | Kalibrasyon kuponları + `PH₃` sarfı + tek-eksen yedekleri (**`$42.250`**) | `%28,5` | Çok-demet MEMS ve `M4` `3 kΩ NbTiN` yedekleri `M2–M4`'e bırakılır |

---

## 3. `M1 v4.0` Fiziksel Mimari ve Sinyal Akışı (`Exp124–135` Kilitli)

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
        │ (5,000 keV 31P+ tek iyon → alansız 0 V wafer, σ_spot=1,428–1,532 nm, σ_tot=3,578–3,620 nm)
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S5.1: s=0,5 UHV Ana Oda (R_iç=182 mm, 34,86 L, ≤10⁻⁸ mbar) — VC-E Masa     │
│  • S4.3: 6-DOF UHV Piezo (43,57 Hz PID + 25 dB FF → σ_stage=0,1024 nm)     │
│          + Zerodur/Invar-36 Kaide (σ_thermal=0,0283 nm @ 20 mK, Exp133)    │
│  • Test Kuponu (f=%1 29Si/28Si Epi, 0 V) + BeCu/Au IBIC Halkası (Ø64/78)   │
│  • S3.2 Soğuk-Ada (100 K) 8-Kanallı IBIC Ön-Uç (204 bileşen, 0 ERC):       │
│      LTC6268 (Cf=0,25 pF, Rf=1 GΩ) → ADA4817-1 (1,2 µs, ×50)               │
│      → DAC8568 (16-bit/ch) + TLV3501 → 49,9 Ω JFPGA → count_hit            │
│      [ENC=24,1 e⁻, η(5 keV, 0,5 pF)=0,99936, C_det≤1,5 pF marjı, Exp127]  │
│  • +Y CF63 S5.5 Flaş Tavlama Portu (Ø44 mm AR safir, 808 nm / 1,0 ms,      │
│      F=41,15 J/cm² ± %5, 10 µs pirometre, MXC <1 K + UHV shutter, Exp130)  │
└───────┬────────────────────────────────────────────────────────────────────┘
        │ (In-line RT load-lock flaş tavlama [0,00 dk kriyo kayıp; f_act=%99,98, σ_anneal=0,328 nm])
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S6.8/S6.1/S6.9: Seyreltme Kriyostatı (MXC ~20 mK) + Ayrıştırılmış PT420    │
│  • S6.9 PT420 Ayrıştırma (ZORUNLU, Exp133 CFG4): 500 mm uzak döner valf +  │
│      600 mm esnek He hattı + k_bellows=2.000 N/m körük + 4× S-halka OFHC   │
│      Cu örgü (k_braid=52,7 N/m, ΔT=3,7 mK) → σ_pointing=0,1473 nm          │
│  • S6.3: 8-Bobinli Aktif Karşı-Sargılı NbTi Mıknatıs (Ø150/36/Ø352 mm):    │
│      Örnekte 1,500000 T ± 17,8 ppm; Quench T_hotspot = 64,6 K (Exp125)     │
│  • z_loc = −155 mm Ø50 mm NbTiN Rezonatör Diski:                           │
│      Nb (RRR>300) Meissner Kabı + Cryoperm-10 → B_res = 22,3 µT (≪0,4 T)   │
│  • 2 Koaksiyel Okuma Zinciri (Ql=800–1200, ≤−100 dBm/ton, 4K HEMT ≤7,8 mW) │
│  • MW (ESR) + RF (ENDOR) Hatları ◄── AWG + ZCU216                          │
│  • [Yan Soket: Exp33 4 K SKY130 İleri-VB Karakterizasyon Testi]            │
└───────┬────────────────────────────────────────────────────────────────────┘
        ▼ (BOED 41,03 ms uyarlamalı {A_k} çıkarımı + G6b ENDOR R1 ölçümü)
[M8: src/machine_control v3.0 (BayesianSpectroscopy + AtlasSelector + GRAPE/XY8 + CellISA v3.0)]
```

> **Kritik Mühendislik Notları (`Exp127` + `Exp133`):**
> 1. **`100 K` Soğuk-Ada IBIC Şartı (`Exp127`):** RT `200 ns / 100 MΩ` CSA `5 keV` Lindhard yükünde (`351 e⁻`) `η = 0,097` ile çöker. IBIC taşıyıcı/CSA modülünün **`~100 K` soğuk-parmak üzerinde `1,2 µs / 1 GΩ`** ile çalıştırılması zorunludur (`ENC = 24,1 e⁻`, `η = 0,99936`).
> 2. **`S6.9` `PT420` Mekanik + Aktif Ayrıştırma Şartı (`Exp133`):** `CAD v3.0` tarzı rijit `PT420` bağlantısı (`CFG1`) `1,4 Hz` ve harmoniklerinde **`σ_stage = 2.051,97 nm`** ile sistemi tamamen bozar; yalnız `25 dB` FF (`CFG5`: `145,59 nm`) veya yalnız mekanik (`CFG2`: `1,006–2,362 nm`) de yetmez. **`S6.9` uzak valf + körük + Cu örgü + `43,57 Hz` PID + `25 dB` harmonik FF (`CFG4`) `M1` gün-1 zorunluluğudur (`σ_stage = 0,1024 nm`).**

---

## 4. Adım-Adım Kurulum, Hizalama ve Kalibrasyon Prosedürü (`Faz A` – `Faz G`)

### Faz A — Temel Altyapı, UHV ve `S6.9` `PT420` Titreşim + Termal Ayrıştırma (`Exp133`)
1. **Zemin & `S6.9` `PT420` Kurulumu:** `VC-E` (tercihen `VC-G`, `3,76×` ek işaretleme payı) tabanlı aktif optik masa, `Zerodur` optik köprü + `Invar-36` kaide (`20 mK` termal kontrol → `σ_thermal = 0,0283 nm`; çıplak `316LN` yasak) ve `6-DOF` UHV piezo (`S4.3`) kurulur. `PT420` soğuk başlığı **`500 mm` uzak döner valf + `600 mm` esnek He hattı + `k_bellows ≤ 6.282` (`2.000 N/m`) 316L CF63 körük + `4×` S-halka OFHC Cu termal örgü (`k_braid ≤ 4.197` [`52,7 N/m`], `ΔT = 3,7 mK`)** üzerinden ayrıştırılır.
2. **Kapalı-Çevrim Servo & Harmonik FF Doğrulaması:** 3-eksen `pm` lazer interferometre (`S4.4`) ile `PT420` (`1,4 Hz` + harmonikler) çalışırken **`43,57 Hz` PID** (`PM ≥ 45°` [model `55,23°`], `GM ≥ 6 dB` [model `8,69 dB`], `||S||_∞ ≤ 1,8` [model `1,676`]) + `25 dB` senkron harmonik FF devredeyken **`σ_stage ≤ 0,25 nm` (model `0,1024 nm`)** ve **`σ_pointing ≤ 0,25 nm` (model `0,1473 nm`)** kanıtlanır.
3. **UHV & Bakeout:** `s=0,5` UHV oda (`R_iç = 182 mm, 34,86 L`) ve `+Y` CF63 `S5.5` safir pencere `He` kaçak testinden (`≤ 10⁻¹⁰ mbar·L/s`) geçirilir; `150 °C` bakeout sonrası **`≤ 10⁻⁸ mbar`** taban basıncı alınır.

### Faz B — `PH₃` Devreye Alma, Kaynak, Wien ve `HDA-HiRes` Süzgeç Kalibrasyonu
1. **EHS İmzalı Ön Koşul:** §5.1 `PH₃` güvenlik testleri (4 dedektör, `< 5 s` otomatik kesme, scrubber) imzalanmadan `PH₃` hattı açılmaz.
2. **İnert Gaz & Kütle Ayrımı:** Önce `Ar/N₂` plazmasıyla `+5 kV / −5 kV` HV kararlılığı (`ΔV/V ≤ 10⁻⁴`) sınanır; ardından `PH₃` ile Wien filtresi (`0,45 T, V_p = 1.348 V`) taranarak `m/q = 31` (`³¹P⁺`) / `32` (`³²PH⁺`, `dx = 0,785 mm = 3,92×` yarık, `R_m = 120,6`) ayrımı doğrulanır.
3. **`HDA-HiRes` Enerji Süzgeci:** `R₀ = 40 mm, E_pass = 100 eV, slit = 0,35 mm` ayarında RFA ile **`ΔE_FWHM ≤ 0,50 eV`** (hedef **`0,453 eV`**) ve Faraday çift-apertürle `B_r` doğrulanır (`Exp124`).

### Faz C — `Arch-B` `10→5 keV` Yavaşlatma Lensi, Blanker ve Demet Nokta Metrolojisi
1. **Blanker Hız Testi:** FPGA `blanker_gate.v` (`100 MHz`) üzerinden `1 µs–1 ms` kare darbelerle sönüm oranı (`> 10⁴`) ve anahtarlama süresi (`< 100 ns`) ölçülür.
2. **`Arch-B` Çalışma Mesafesi & Bıçak-Kenarı Profili:** Wafer `0 V` toprak potansiyelinde, **`WD = 0,250 mm`** (`E_gap = 10,60 MV/m ≤ 12 MV/m`) `S9.1` bıçak-kenarı hedefiyle **`σ_spot ≤ 1,50 nm`** (`1,428 nm @ 10 ms`; `1,532 nm @ 15 ms`) doğrulanır (`Exp124`).
3. **Kafa–Kademe Matrisi:** Fiducial işaretlerle piezo–interferometre–blanker kalıntısı `< 0,25 nm` altına çekilir (`Exp135` birleşik `σ_tot = 3,578–3,620 nm`).

### Faz D — `100 K` Soğuk-Ada IBIC Kalibrasyonu ve Sayılmış Tek-İyon İmplantasyonu
1. **`100 K` Soğuk-Ada CSA Kalibrasyonu:** `src/board/` 8-kanallı kartı `100 K` soğuk adaya bağla (`< 5 cm` PTFE mikro-koaksiyel, `C_par < 0,15 pF`); `τ = 1,2 µs`, `R_f = 1 GΩ`, kazanç `×50,0`, **`ENC ≤ 25–30 e⁻`** (`24,1 e⁻ @ 0,5 pF`), `DAC8568` `5,5σ` eşiklerinde `P_false < 10⁻³ / 1 ms` (`2,59×10⁻⁴`) doğrula (`Exp127`).
2. **`5 keV ³¹P⁺` Tek-İyon Sayımı:** Gerçek Lindhard `341,7 e⁻` pikiyle hizala; `blanker_gate.v` (`1 ms` watchdog) kapalı çevriminde **`η ≥ 0,99`** (model **`0,99936 @ 0,5 pF`**, `0,9906 @ 1,5 pF`) kanıtla.

### Faz E — Mod B Kupon İmplantasyonu ve `S5.5` `808 nm / 1,0 ms` Flaş Tavlama (`Exp130`)
1. **Kupon Yazımı:** `f = %1,0` `²⁹Si / ²⁸Si` epitaksiyel kuponuna (`S5.4`, `5`-yonga deneme lotu) referans ızgarasında `64` (tercihen `128` — `G6b` istatistik gücü için) aday yuva (`N = 1` sayılmış `³¹P⁺`/yuva) yaz; tüm atışları `ShotRecord` JSONL veritabanına aktar.
2. **`S5.5` `808 nm / 1,0 ms` Flaş Tavlama (`Exp130` Risk `R6` Doğrulaması):** Fırın (`600 °C/10 dk`: `%93,2` yüzey yığılması) ve RTA (`1000 °C/10 s`: `σ = 4,97 nm`, `%21,2` kayıp) **yasaktır**. İn-line oda sıcaklığı load-lock konumunda (`0,00 dk / 0 J` kriyo kayıp; `MXC < 1 K` kilit + UHV emniyet perdesi kapalıyken) `+Y` CF63 AR safir pencereden (`Ø44 mm CA`, `T_AR = %98`, `9,47×` LIDT) **`808 nm` diyot lazer / `1,0 ms` darbe / `F = 41,15 J/cm² ± %5`** (`T_peak = 1440,3 K`, arka yüz `592,9 K`) uygula ve `10 µs` çift-renkli pirometreyle profili kaydet. İkiz kuponda SIMS / `4 K` iletimle **`f_act ≥ %85`** (model **`%99,98`**), **`σ_anneal ≤ 0,50 nm`** (model **`0,328 nm`**), yüzey+vakum kaybı `< %1` (model `%0,022`) ve `²⁹Si` karışma `σ_iso < 0,1 nm` (model `0,0314 nm`) doğrula.

### Faz F — `MXC` Soğutma, `8`-Bobinli Mıknatıs (`1,50 T / 22,3 µT`) ve Yan SKY130 Testi
1. **Manyetik Harita (`R7` Fiziksel Doğrulama):** `8`-bobinli `S6.3` mıknatısını `1,500000 T`'ye rampa et (`I/I_c ≤ 0,212`); NMR/Hall ile yonga merkezinde **`ΔB/B ≤ 100 ppm`** (model `17,81 ppm`), `z_loc = −155 mm` `Nb (RRR>300)` + `Cryoperm-10` kabı içinde **`B_res ≤ 0,40 T`** (model **`22,3 µT`**, `B_perp ≤ 10 mT`) ve kontrollü quench (`≤ 65–100 K`, model `64,6 K`) doğrula (`Exp125`).
2. **Kriyo & `2`-Zincirli RF Okuma:** `MXC ≤ 20–25 mK`, `4 K` yükü `< 0,20 W`, `S6.9` Cu örgü `ΔT ≤ 10 mK` (`3,7 mK`), `NbTiN` `Q_l = 800–1200`, `ton ≤ −100 dBm/kanal`, `SNR = 10` entegrasyon süresi `≤ 0,1 ms` (`0,0627 ms` model) ölç.
3. **İsteğe Bağlı `Exp33` Yan Kuponu:** `4 K` plakasındaki yan sokette SKY130 ileri-`V_B` ve çift-yönlü histerezis ölçümü (`C33-2/C33-5`).

### Faz G — Kapalı Çevrim II: `BOED` Spektroskopi, **`G6b` `ENDOR` Risk `R1` Ölçümü** & `CellISA v3.0` (`Exp126/129/132`)
1. **`BOED` Uyarlamalı Ölç & Seç (`Exp132`):** Aday yuvalarda `src/machine_control/adaptive_spectroscopy.py` (`--preset v400`, `$0` ek donanım) ile 3-aşamalı uyarlamalı Elzerman + ESR/ENDOR çalıştır; ortalama sürenin `1.000 ms`'den **`≤ 80 ms`** (model **`41,03 ms`**, medyan `23,04 ms`, boş yuva `0,73 ms`) düzeyine indiğini, frekans hatasının **`RMS ≤ 150 Hz`** (model **`72,67 Hz`**) ve `FNR ≤ %1` (`%0,20`), `FPR ≤ %0,5` (`%0,00`) olduğunu kanıtla. `AtlasSelector` ile en az `1` (hedef `≥ 3`) `K=8` / `K=4` yazmaç seç (`min_spacing ≥ 5 kHz`, Vandermonde `8/8`, `D0 ≤ 10⁻⁶`).
2. **`G6b` — Kritik Risk `R1` (`Exp129`) `ENDOR` Verim & Aralık Kapısı:** `Exp129` (`VOKL-6` 6-vadi merkez-hücre modeli), `KL`'ye kıyasla güçlü site sayısında (`18.784 → 6.091 / 9.464`) ve `f = %1` tek-atış çalışma veriminde aşağı yönlü risk tespit etmiştir (**`KL %50,50`** vs **`VOKL-6 HM5962 %33,25`** vs **`VOKL-6 norm %4,75`**, `min_gap < 6,893 kHz` oranı `%57,9–%73,7`). `M1` kuponunda ölçülen `≥ 64` donorun deneysel `ENDOR` spektrumuyla gerçek `p_work(f=%1)` ve en yakın komşu aralığı histogramı çıkarılır:
   - **`p_work ≥ %30` (`HM5962` / `KL` bandı):** `M3` `BOED` ile hâlâ yazma-tavanlıdır (`0,98–1,50×10⁹/gün`); `M4` `N_cand*` (`6` vs `11` veya `f = %2` → `6`) kesinleşir.
   - **`p_work < %15` (`VOKL-6 norm` kırmızı çizgisi):** `M4` `N_cand*` patlar (`86`); `M2–M4` öncesi **`f = %2`–`%3` epitaksi** veya `4`-çekirdek `K=4` yazmaç yeniden tasarımı zorunlu olur!
3. **Kalibre Et & `CellISA v3.0` Koştur (`Exp126/132`):** RF NMR bobininde **`10–15 kHz` Rabi genlik payı (`B₁ ≈ 1,2–1,8 mT`)** doğrulandıktan sonra 9-köşeli (`±400 Hz × ±%2`) iki-aşamalı 32B **`XY8`-GRAPE** sentezle (**`CPMG` yasak**; **`N_total = 32–64`**, **`N = 32` global optimum `0,9260 / 0,9648`**, **`N = 128` DDRF duvarı yasak**; `ε ≤ 10⁻³`); `CellISA v3.0` (`14` komut) ile `Bell` (`0,9501`), `GHZ-4` (`0,9401`), `Grover-2` (`P(\|11⟩) = 0,9237`), `BitFlip-3` (`0,8878`) ve `QFT-3` (`0,8377`) programlarını koşturup tomografiyle **`Q_32D ≥ 0,85`** ve **`D0(17,5 s) ≤ 10⁻⁶`** (model `≤ 7,76×10⁻⁹`) doğrulayarak ilk fiziksel SHA-256 `ProgramCertificate` kaydını mühürle.

---

## 5. Zorunlu EHS ve Laboratuvar Güvenlik Protokolleri

### 5.1 `PH₃` (Fosfin) Toksik ve Piroforik Gaz Güvenliği — **KRİTİK ÖNCELİK**
Fosfin (`PH₃`) renksiz, solunumla hızla ölümcül ve saf hâlde piroforik bir gazdır (`OSHA PEL = 0,3 ppm` 8 saat TWA; `ACGIH TLV-STEL = 1,0 ppm`; `NIOSH IDLH = 50 ppm`) `{Literatür}`:
1. **Düşük Riskli Kaynak:** Sertifikalı seyreltik karışım (`%1–%5 PH₃` in `H₂`/`Ar`) veya sub-atmospheric adsorban tüp (**SDS/SAGE**) zorunludur.
2. **Muhafaza & Borulama:** SEMI S2 / NFPA 318 negatif basınçlı sürekli egzozlu çift-tüplü gaz kabini (`S1.6`), elektro-parlatılmış çift-cidarlı `316L VAR` metal VCR borulama (pirinç/elastomer yasak), otomatik `N₂` süpürme manifoldu.
3. **4-Nokta Sürekli Dedektör & SIL-2 PLC (`S7.4-04`):** Kabin, egzoz, kaynak başlığı ve solunum bölgesi dedektörleri (Alarm-1 `0,15 ppm` uyarı; Alarm-2 `0,30 ppm` `< 5 s` otomatik pnömatik silindir kapama + HV/plazma kesme + tahliye sireni; tümü UPS destekli).
4. **Arıtım (Scrubber):** Yağsız kuru ön-pompa çıkışı doğrudan sertifikalı kuru-reçine/ıslak scrubber'a (`< 50 ppb` çıkış) bağlanır; iki kişilik (buddy) çalışma ve erişilebilir SCBA zorunludur.

### 5.2 Yüksek Gerilim (`±5 kV` / `10–20 kV`), `S5.5` Sınıf-4 Lazer, X-Işını, Kriyo, `1,50 T` Mıknatıs ve ESD
- **HV & X-Işını:** `+5 kV` anot ve `−5 kV` üst kolon gömleği akım sınırlı (`≤ 5 mA` kaynak, `≤ 1 mA` lensler), kapı interlock'lu ve LOTO + topraklama kancalıdır; devreye almada `< 0,5 µSv/h` Bremsstrahlung taraması yapılır.
- **`S5.5` Sınıf-4 `808 nm` Flaş Tavlama Lazeri (`Exp130`):** Tam kapalı ışın tüpü, kapı/port interlock'u, `OD ≥ 7 @ 808 nm` koruyucu gözlük, `MXC < 1 K` kriyo kilidi + pnömatik UHV emniyet perdesi (yanlışlıkla soğuk aşamaya ateşlemeyi donanımsal olarak engeller), `10 µs` pirometre aşırı-sıcaklık kesmesi (`T > 1580 K` anlık kesme — ergime `1687 K` altında güvenlik marjı).
- **Kriyo ODH & Quench:** Sürekli `O₂` monitörü (`< %19,5` uyarı, `< %18,0` tahliye), çift kademeli basınç tahliyesi, dış atmosfere yönlendirilmiş quench egzoz hattı (`T_hotspot = 64,6 K`, `R_dump = 1,563 Ω`).
- **Manyetik Alan (`1,50 T`):** `0,5 mT` (`5 Gauss`) hattı işaretli; kalp pili yasak bölgesi; yalnız `Ti`/`BeCu`/pirinç aletler.
- **İnterferometre & ESD:** İnterferometre kapalı ışın tüpü; `< 50 V` HBM hassas IBIC/`NbTiN`/SET cihazları için ANSI/ESD S20.20 topraklı istasyon ve iyonlaştırıcı.

---

## 6. `M1 v4.0` Go/No-Go Çıkış Kapıları (`G1`–`G8`, `G6b` Dahil — `Exp124–135` Kilitli)

> Aşağıdaki 9 kapının tamamı geçilmeden `M2` (`10²–10³` demetcikli MEMS prototip) ve `M4` cQED yatırımına geçilmez.

| Kapı | Alt Sistem / Faz | Kilitli Kabul Eşiği (Go Kriteri) | Doğrulama Yöntemi | No-Go / Düzeltme Kuralı |
|---|---|---|---|---|
| **`G1`** | EHS, UHV & `S6.9` `PT420` (`Faz A–B`, `Exp133`) | Tüm `PH₃`/Sınıf-4 lazer/HV/O₂/PLC interlock `%100` PASS (`< 50 ppb`, `< 5 s`); UHV `≤ 10⁻⁸ mbar`; `PT420` açıkken `S6.9` `CFG4` ile **`σ_stage ≤ 0,25 nm`** (`0,1024 nm`), **`σ_pointing ≤ 0,25 nm`** (`0,1473 nm`), **`σ_thermal ≤ 0,10 nm`** (`0,0283 nm`) | EHS tutanağı, RGA, interferometre PSD, PID Bode (`PM≥45°`) | Güvenlik kilidi geçmeden gaz/lazer/HV açılamaz; `σ_stage > 0,25 nm` ise `k_bellows`/Cu örgü/FF harmonikleri sıkılaştırılır (`VC-G` ops.) |
| **`G2`** | İyon Kolonu (`Faz B–C`, `Exp124`) | Wien `m/q=31` ayrımı (`R_m ≥ 60`, hedef `120,6`); `HDA-HiRes` **`ΔE_FWHM ≤ 0,50 eV`** (`0,453 eV`); `Arch-B` `WD = 0,250 mm`, `E_gap ≤ 12 MV/m` (`10,60 MV/m`), **`σ_spot ≤ 1,50 nm` @ `5 keV`** (`1,428 nm`) | Wien taraması, RFA, Faraday `B_r`, bıçak-kenarı profili | `σ_spot > 1,6 nm` ise `HDA` yarık daraltılır veya `LMIS` opsiyonu değerlendirilir |
| **`G3`** | Soğuk-Ada IBIC (`Faz D`, `Exp127`) | `100 K` soğuk adada `LTC6268` CSA (`1,2 µs / 1 GΩ`): `C_det ≤ 1,5 pF` (`0,5 pF`), **`ENC ≤ 30 e⁻`** (`24,1 e⁻`), `P_false < 10⁻³ / 1 ms`, **`η ≥ 0,99` @ `5 keV`** (`0,99936`), `blanker_gate` `1 ms` watchdog PASS | Test pulser, Lindhard `341,7 e⁻` PHA piki, FPGA sayım logu | RT'de çalıştırma yasak; `η < 0,99` ise kablo `< 5 cm` / `100 K` temas kontrol edilir (acil yedek `10 keV` `η=0,9998`) |
| **`G4`** | `S5.5` Flaş Tavlama (`Faz E`, `Exp130`, `R6`) | `808 nm / 1,0 ms / F = 41,15 J/cm² ± %5` (`T_peak = 1440,3 K` pirometre doğrulamalı): aktivasyon **`f_act ≥ %85`** (model `%99,98`), **`σ_anneal ≤ 0,50 nm`** (`0,328 nm`), kayıp `< %1` (`%0,022`), `σ_iso < 0,1 nm` (`0,0314 nm`) | `10 µs` pirometre logu, ikiz kupon SIMS / `4 K` Hall-iletim | Fırın/RTA yasak; `σ_anneal > 0,5 nm` ise darbe `0,5–0,8 ms`'ye kısaltılıp akı yeniden ayarlanır |
| **`G5`** | Mıknatıs & Kriyo (`Faz F`, `Exp125/133`) | `MXC ≤ 25 mK`, `B_z = 1,500000 T` (`ΔB/B ≤ 100 ppm`, `17,8 ppm`), `z_loc = −155 mm` kalkanlı **`\|B_res\| ≤ 0,40 T`** (`22,3 µT`, `\|B_perp\| ≤ 10 mT`), quench `≤ 100 K` (`64,6 K`), Cu örgü `ΔT ≤ 10 mK` (`3,7 mK`), `NbTiN Q_l = 800–1200`, `SNR=10 ≤ 0,1 ms` | Termometri, NMR/Hall 3B harita, VNA `S21`, FAT quench | `\|B_res\| > 0,40 T` ise karşı-sargı akımı / `Nb` kalkan oturuşu ayarlanır |
| **`G6a`** | `BOED` Tek-Donor ESR/ENDOR (`Faz G`, `Exp132`) | `f = %1,0` Mod B kuponunda tek-atış okuma sadakati `≥ %95`, `BOED` ortalama süre **`≤ 80 ms`** (`41,03 ms`), **`RMS ≤ 150 Hz`** (`72,67 Hz`), `FNR ≤ %1`, `FPR ≤ %0,5`, en az `1` (hedef `≥ 3`) `K=8` / `K=4` yazmaç seçimi | Elzerman + `BayesianSpectroscopy` (`--preset v400`) + `AtlasSelector` | `RMS > 200 Hz` ise `BOED` durdurma eşiği sıkılaştırılır veya klasik `1 s` taramaya düşülür |
| **`G6b`** | **Risk `R1` `ENDOR` Verim Kapısı (`Faz G`, `Exp129/135`)** | `≥ 64` donorda ölçülen `f = %1` gerçek çalışma verimi **`p_work ≥ %30`** (`HM5962 %33,25` – `KL %50,50` bandı) ve `min_gap < 6,893 kHz` fraksiyonu kayıtlı; `M4` `N_cand*` (`6` vs `11` / `f=%2`) bu ölçüme göre kilitlenir | `≥ 64`-yuva deneysel `ENDOR` istatistiği & `Exp129/135` yeniden kalibrasyonu | **`p_work < %15` (`VOKL-6 norm %4,75` kırmızı çizgisi)** çıkarsa `M2/M4` dondurulur; **`f = %2`–`%3` epitaksi** veya `K=4` yazmaç revizyonu zorunlu olur |
| **`G7`** | GRAPE + `XY8` DD & `CellISA v3.0` (`Faz G`, `Exp126/132`) | RF bobin Rabi payı **`10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`)**, zorunlu **`XY8` `N_total = 32–64`** (`N=32` optimum `0,9260/0,9648`, `N=128` ve `CPMG` yasak), `ε ≤ 10⁻³`, **`D0(17,5 s) ≤ 10⁻⁶`** (`≤ 7,76×10⁻⁹`), **`Q_32D ≥ 0,85`**, `CellISA v3.0` SHA-256 sertifikası | 32B durum tomografisi + `ProgramCertificate` JSONL + `XY8` eksen testi | `Q < 0,85` ise **`N = 128`'e çıkılmaz** (`sp_ovl=0,0972` DDRF duvarı!); `N = 32` optimumuna dönülür, `10–15 kHz` RF payı sıkılaştırılır |
| **`G8`** | Maliyet, `7-RFQ` & 5y TCO Kapısı (`Exp128 v4.0` + `Exp134`) | `M1 v4.0` faturaları (`~$2,34M` ref., 5y Lab TCO `$8,62M`) + **`7-RFQ`** bağlayıcı teklifleriyle (`%92,6` BOM varyansı) güncellenen `Exp128 v4.0` `M3` Program `P50 ≤ $50M` (`$30,87M`), **`P(>$100M) < %5`** (`%3,38`), `Exp134` 5y Fab TCO `$16,07M` | `7-RFQ` uzlaştırması + `run_exp128.py` + `run_exp134.py` + `BUTCE_DURUMU.md` | `> $50M` ise gerekçe `BUTCE_DURUMU.md`'ye işlenir; `> $100M` ise ölçek/`4–8 GHz` bandı/`1 K` filo revizyonu zorunludur |
