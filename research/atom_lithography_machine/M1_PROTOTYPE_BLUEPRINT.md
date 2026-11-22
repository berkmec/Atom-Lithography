# `M1` Fiziksel Laboratuvar Prototipi Tasarım ve Kurulum Planı (`M1_PROTOTYPE_BLUEPRINT`)

**Sürüm:** v2.1 (Tam Faz-2B Kilitli — `Exp124–128`, `CAD v3.0`, `CellISA v2.0`, `BOM_DETAILED` — 2026-11-23; v1.0 taslak: 2026-11-22).  
**Dayanak:** [DESIGN.md](DESIGN.md), [MODULAR.md](MODULAR.md) (v3.0-ICD), [BOM_DETAILED.csv](BOM_DETAILED.csv), [BOM_ENGINEERING.md](BOM_ENGINEERING.md), [RFQ_SPECIFICATIONS.md](RFQ_SPECIFICATIONS.md), [LITERATURE.md](LITERATURE.md), [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md), `results/exp124..128*`.

> **Epistemik Sınır ve Amaç:** Bu belge, `M0` (teori/model/EDA) aşamasından ilk fiziksel laboratuvar gösterimine (**`M1` — tek-demet sayılmış implantasyon + tek-yuva ölç–seç–kalibre–programla**) geçişin eksiksiz mühendislik planıdır. **Projede henüz laboratuvar ölçümü, tedarikçi teklifi veya üretilmiş donanım yoktur (`no_lab_measurement=true`, `no_supplier_quotes=true`).** `Exp124`, `Exp125`, `Exp126`, `Exp127` ve `Exp128` sayısal hedeflerinin tamamı aşağıda mühürlenmiştir.

---

## 1. `M1` Görev Tanımı, Bütçe Özeti ve Çıkış Ölçütü
- **Tek Cümlelik Hedef:** Seyreltik epitaksiyel `²⁹Si` banyosu (`f = %1,0`, Mod B — donör saçılmasından etkilenmeyen baz mod, `Exp124 CD8`) taşıyan bir `²⁸Si` test kuponu üzerinde, tek-demet `10→5 keV` sayılmış `³¹P⁺` implantasyonu + `100 K` soğuk-ada IBIC tek-iyon algılaması + ms flaş tavlama + `MXC` (`~20 mK`, `1,500000 T`) tek-donor ESR/ENDOR spektroskopisi + yazmaç-özgü GRAPE/XY8 senteziyle **en az bir (hedef: `≥ 3`) sertifikalı `K=8` (veya evrensel `K=4` altküme) çekirdek-spin yazmacını fiziksel olarak doğrulamak ve `CellISA` üzerinden `Bell`/`GHZ` programını koşturmak** `[DESIGN.md §10 | M1]`.
- **Finansal ve Stratejik Mantık (`Exp128` / `BOM_ENGINEERING.md`):**
  - `M1` nominal donanım maliyeti: **`$2.189.770`** (`P10–P90`: `$1,28M–$3,94M`; `M3` `$4.189.600` toplamının **`%52,3`'ü**). Tahmini program bedeli (`×3–×5,5–×10`): `$6,6M – $12,0M – $21,9M` (`$50M` yumuşak sınırın yarısının altında).
  - **Yüksek Yatırım Koruması:** `M1` donanım bedelinin yaklaşık **`%82`'si (`~$1,80M`)** (`20 mK` DR `$720k`, `PT420`, `8`-bobinli `1,50 T` mıknatıs `$185k`, UHV oda/pompalar, `PH₃` gaz kabini/scrubber, `6-DOF` piezo, lazer interferometre, `HDA-HiRes` enerji süzgeci, `10→5 keV` kolon) doğrudan `M3` altın ölçek makinesinin çekirdek gövdesine taşınır — **`M1` çöpe giden tek kullanımlık bir düzenek değil, modüler (`MODULAR.md`) yükseltilebilir ana platformdur.**
  - **Kaldırılan Birincil Riskler:** `M1`, `M3`'teki en ağır iki `R&D` ve tedarik riskini (`S2.1–S2.3` çok-demet MEMS NRE `$661k` ve `S6.6` `56`-zincir `B/C` duvarı `%77,3` varyans) ve SKY130 çip tape-out bağımlılığını (`R5/Exp123`) tamamen dışarıda bırakır.

---

## 2. `M3` (Altın Ölçek) → `M1` (Tek-Demet Prototip) Alt-Sistem İndirgeme Tablosu (`Exp128` Kilitli)

| Alt Sistem | `M3` Altın Ölçek (`$4.189.600` Nom) | `M1` Tek-Demet Prototipi (`$2.189.770` Nom) | `M1` Payı | Kilitli Fizik / Mühendislik Şartnamesi (`Exp124–128`) |
|---|---|---|---:|---|
| **`S1` Kaynak & Kolon** | Çift hat (`³¹P⁺/²⁹Si⁺`), `$416.000` | **Tek hat (`³¹P⁺`, Mod B)** duoplazmatron + `PH₃` kabini/scrubber + Wien + `HDA-HiRes` + `10→5 keV` kolon (**`$319.750`**) | `%76,9` | Kolon `562,66 mm / Ø110 mm / 25,92 kg`; Wien `0,45 T, 150 mm, R_m=120,6`; **`HDA-HiRes`** (`R₀=40 mm, ΔE_FWHM=0,453 eV`); wafer `0 V`, üst gömlek `−5 kV`, anot `+5 kV` (`Exp124`) |
| **`S2` Yazma Kafası** | **`32×32 = 1.024` eş-adımlı `0,50 mm`** MEMS apertür/blanker/`Arch-B` (`16×16 mm < Ø28 mm`, `16×` 64-ch karo), `$775.500` | **Tek-delikli mikro-apertür + tek kanal blanker + tek eksenli `Arch-B` yavaşlatıcı lens** (**`$147.750`**) | `%19,1` | **`Arch-B`**: `WD = 0,250 mm`, `E_gap = 10,60 MV/m`, `C_c = 2,660 mm`, `C_s = 10,786 mm`, **`σ_spot = 1,428 nm`** (`Ti=0,25 eV, 10 ms` / LMIS `1 ms`; kanonik `15 ms`: `1,532 nm`), `σ_tot = 3,674–3,715 nm` (`Exp124`) |
| **`S3` Soğuk-Ada IBIC Algılama** | `16×8` kanal vakum-içi CSA + çok-karolu FPGA, `$224.000` | **`1–2` adet 8-kanallı `100 K` soğuk-ada IBIC kartı (`src/board/`) + 1 adet FPGA kartı (`blanker_gate.v`)** (**`$88.550`**) | `%39,5` | **KRİTİK `Exp127` KİLİDİ:** RT `200 ns` `5 keV`'de `η=0,097` FAIL! **`100 K` soğuk adada `LTC6268` CSA (`Cf=0,25 pF, Rf=1 GΩ`) + `ADA4817-1` (`τ=1,2 µs, ×50`) + `DAC8568` + `TLV3501` (`204` parça, `0` ERC):** **`ENC = 24,1 e⁻`**, **`η(5 keV, 0,5 pF) = 0,99936`**, `C_det ≤ 1,5 pF` marjı, `P_false = 2,59×10⁻⁴ / 1 ms` |
| **`S4` Konum & İnterferometri** | Granit + aktif tabla + 6-DOF piezo + 3-eksen interferometre, `$253.000` | Aynı yalıtım & `6-DOF` UHV piezo + 2/3-eksen `pm` interferometre + `Invar` kaide (**`$233.920`**) | `%92,5` | `σ_kademe ≤ 0,50 nm` RMS (`0,5–500 Hz`), `Invar` kaide (`R=45..52 mm`, `4,0 mm` radyal pay, `CAD v3.0`) |
| **`S5` UHV & Flaş Tavlama** | `s=0,5` UHV oda (`34,86 L`) + load-lock + `25`-yonga epi lotu, `$243.000` | Aynı UHV oda/pompa/flaş tavlama + **`5`-yonga `f=%1,0` deneme epi lotu** (**`$196.800`**) | `%81,0` | UHV `≤ 10⁻⁸ mbar`, `R_iç=182 mm`, ms flaş tavlama (`σ_tavlama ≤ 0,5 nm`, `600 °C/10 dk` göç eşiği altı) |
| **`S6` Kriyo, Mıknatıs & Okuma** | `20 mK` DR + `PT420` + `8`-bobin `1,5 T` + **`56` zincir**, `$1.925.900` | **Aynı `20 mK` DR (`$720k`) + `PT420` + `8`-bobin `1,50 T` mıknatıs (`$185k`) + yalnız `2` okuma zinciri** (**`$1.056.300`**) | `%54,8` | `8`-bobin `Ø150 / 36 mm / Ø352`, **`1,500000 T ± 17,8 ppm`**, **`Nb RRR>300` + `Cryoperm-10` ile `B_res = 22,3 µT`**, **`T_quench = 64,6 K`**; `2` zincir `4 K < 0,12 W`, `MXC < 2,2 µW`; `20 mK` baz `EVPI@N=1 = $0` (`Exp125/128`) |
| **`S7–S8` Kontrol & `CellISA`** | `2×` GPU + çok-şase AWG + SKY130 MPW, `$204.200` | `1×` GPU iş istasyonu + `1×` AWG + `1×` `ZCU216` + `1×` EMI kabin + **`machine_control` v2.0 & `CellISA`** (**`$104.450`**) | `%51,2` | `SKY130` MPW `M2`'ye ötelenir; `CellISA` canlı `bell/ghz/repcode3/qft3` + SHA-256 JSONL sertifika (`Exp127`) |
| **`S9` Sarf & Yedek** | Tam yedek MEMS/LNA + 1 yıllık gaz, `$148.000` | Kalibrasyon kuponları + `PH₃` sarfı + tek-eksen yedekleri (**`$42.250`**) | `%28,5` | Çok-demet MEMS yedekleri `M2/M3`'e bırakılır |

---

## 3. `M1` Fiziksel Mimari ve Sinyal Akışı (`Exp124` + `Exp125` + `Exp127` Kilitli)

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
        │ (5,000 keV 31P+ tek iyon → alansız 0 V wafer, σ_spot=1,428–1,532 nm, σ_tot=3,674–3,715 nm)
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S5.1: s=0,5 UHV Ana Oda (R_iç=182 mm, 34,86 L, ≤10⁻⁸ mbar) — Optik Masa    │
│  • S4.3: 6-DOF UHV Piezo (σ_kademe ≤ 0,5 nm) + Invar Kaide + İnterferom.   │
│  • Test Kuponu (f=%1 29Si/28Si Epi, 0 V) + BeCu/Au IBIC Halkası (Ø64/78)   │
│  • S3.2 Soğuk-Ada (100 K) 8-Kanallı IBIC Ön-Uç (204 bileşen, 0 ERC):       │
│      LTC6268 (Cf=0,25 pF, Rf=1 GΩ) → ADA4817-1 (1,2 µs, ×50)               │
│      → DAC8568 (16-bit/ch) + TLV3501 → 49,9 Ω JFPGA → count_hit            │
│      [ENC=24,1 e⁻, η(5 keV, 0,5 pF)=0,99936, C_det≤1,5 pF marjı, Exp127]  │
└───────┬────────────────────────────────────────────────────────────────────┘
        │ (Yük-kilidi transferi → ms Flaş Tavlama → MXC Taşıyıcı Montajı)
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S6.8/S6.1: Seyreltme Kriyostatı (MXC ~20 mK; PT420 4 K Ön-Soğutucu)        │
│  • S6.3: 8-Bobinli Aktif Karşı-Sargılı NbTi Mıknatıs (Ø150/36/Ø352 mm):    │
│      Örnekte 1,500000 T ± 17,8 ppm; Quench T_hotspot = 64,6 K (Exp125)     │
│  • z_loc = −155 mm Ø50 mm NbTiN Rezonatör Diski:                           │
│      Nb (RRR>300) Meissner Kabı + Cryoperm-10 → B_res = 22,3 µT (≪0,4 T)   │
│  • 2 Koaksiyel Okuma Zinciri (Ql=800–1200, ≤−100 dBm/ton, 4K HEMT ≤7,8 mW) │
│  • MW (ESR) + RF (ENDOR) Hatları ◄── AWG + ZCU216                          │
│  • [Yan Soket: Exp33 4 K SKY130 İleri-VB Karakterizasyon Testi]            │
└───────┬────────────────────────────────────────────────────────────────────┘
        ▼ (Ölçülen {A_k} spektrumu → Kapalı Çevrim II)
[M8: src/machine_control v2.0 (AtlasSelector + GRAPE/XY8 + CellISA SHA-256)]
```

> **Kritik Mühendislik Notu (`Exp127` Soğuk-Ada IBIC Şartı):** `Exp127`, oda sıcaklığındaki `200 ns / 100 MΩ` CSA'nın gerçek Lindhard `5 keV ³¹P⁺` yükünde (`351 e⁻`) `ENC = 89,9 e⁻` nedeniyle `η = 0,097` ile çöktüğünü kanıtlamıştır. Bu nedenle `M1` yazma odasında **IBIC taşıyıcı/CSA modülünün `~100 K` soğuk-parmak (LN₂ veya kriyo-soğutucu 50–100 K kademesi) üzerinde ve `1,2 µs / 1 GΩ` zaman sabitiyle çalıştırılması zorunludur** (`ENC = 24,1 e⁻`, `η = 0,99936`). Alternatif olarak RT ön-devreye alma yalnız `10 keV` kalibrasyon modunda (`1,2 µs / 1 GΩ`, `η = 0,9998`) yürütülür.

---

## 4. Adım-Adım Kurulum, Hizalama ve Kalibrasyon Prosedürü (`Faz A` – `Faz G`)

### Faz A — Temel Altyapı, UHV ve Titreşim Zemini
1. **Zemin & İzolasyon:** Aktif sönümlemeli optik masa (`0,5–100 Hz`) ve `6-DOF` UHV piezo kademesi (`S4.3`) kurulur; 3-eksen `pm` lazer interferometre (`S4.4`) ile `PT420` darbesi (`1,4 Hz`) açıkken dahi kapalı-çevrim artık titreşimin **`σ_kademe ≤ 0,50 nm` RMS** (`0,5–500 Hz`) olduğu doğrulanır.
2. **UHV & Bakeout:** `s=0,5` UHV oda (`R_iç = 182 mm, 34,86 L`) ve yük-kilidi `He` kaçak testinden (`≤ 10⁻¹⁰ mbar·L/s`) geçirilir; `150 °C` bakeout sonrası turbo+iyon+TSP ile **`≤ 10⁻⁸ mbar`** taban basıncı ve temiz RGA spektrumu alınır.

### Faz B — `PH₃` Devreye Alma, Kaynak, Wien ve `HDA-HiRes` Süzgeç Kalibrasyonu
1. **EHS İmzalı Ön Koşul:** §5.1 `PH₃` güvenlik testlerinin tamamı (4 dedektör, `< 5 s` otomatik kesme, scrubber) imzalanmadan `PH₃` hattı açılmaz.
2. **İnert Gaz & Kütle Ayrımı:** Önce `Ar/N₂` plazmasıyla `+5 kV / −5 kV` HV kararlılığı (`ΔV/V ≤ 10⁻⁴`) sınanır; ardından `PH₃` ile Wien filtresi (`0,45 T, V_p = 1.348 V`) taranarak `m/q = 31` (`³¹P⁺`) ile `32` (`³²PH⁺`, `dx = 0,785 mm = 3,92×` yarık, `R_m = 120,6`) temiz ayrımı doğrulanır.
3. **`HDA-HiRes` Enerji Süzgeci:** `R₀ = 40 mm, E_pass = 100 eV, slit = 0,35 mm` ayarında RFA ile **`ΔE_FWHM ≤ 0,50 eV`** (hedef **`0,453 eV`**) ve Faraday çift-apertürle `B_r` indirgenmiş parlaklığı doğrulanır (`Exp124`).

### Faz C — `Arch-B` `10→5 keV` Yavaşlatma Lensi, Blanker ve Demet Nokta Metrolojisi
1. **Blanker Hız Testi:** FPGA `blanker_gate.v` (`100 MHz`) üzerinden `1 µs–1 ms` kare darbelerle sönüm oranı (`> 10⁴`) ve anahtarlama süresi (`< 100 ns`) ölçülür.
2. **`Arch-B` Çalışma Mesafesi & Bıçak-Kenarı Profili:** Wafer `0 V` toprak potansiyelinde, **`WD = 0,250 mm`** çalışma mesafesinde (`E_gap = 10,60 MV/m ≤ 12 MV/m` hi-pot doğrulamalı) `S9.1` bıçak-kenarı (knife-edge) hedefi taranarak **`σ_spot ≤ 1,50 nm`** (hedef **`1,428 nm`** @ `10 ms` / `Ti=0,25 eV`; `1,532 nm` @ `15 ms` / `Ti=0,5 eV`) doğrulanır (`Exp124`).
3. **Kafa–Kademe Matrisi:** Fiducial işaretlerle piezo–interferometre–blanker hizalama kalıntısı `< 0,5 nm` altına çekilir.

### Faz D — `100 K` Soğuk-Ada IBIC Kalibrasyonu ve Sayılmış Tek-İyon İmplantasyonu
1. **`100 K` Soğuk-Ada CSA Kalibrasyonu:** `src/board/` 8-kanallı kartı `100 K` soğuk adaya bağla (`< 5 cm` PTFE mikro-koaksiyel, `C_par < 0,15 pF`); kalibrasyon pulserı ile `τ = 1,2 µs`, `R_f = 1 GΩ`, net kazanç `×50,0`, **`ENC ≤ 25–30 e⁻`** (model **`24,1 e⁻ @ 0,5 pF`**) ve `DAC8568` kanal-başı `5,5σ` eşiklerinde `P_false < 10⁻³ / 1 ms` (`2,59×10⁻⁴`) doğrula (`Exp127`).
2. **`5 keV ³¹P⁺` Tek-İyon Sayımı:** Düşük akımda PHA spektrumunu gerçek Lindhard `341,7 e⁻` pikiyle hizala; `blanker_gate.v` (`1 ms` watchdog) kapalı çevriminde **`η ≥ 0,99`** (model **`0,99936 @ 0,5 pF`**, `0,9906 @ 1,5 pF`) kanıtla.

### Faz E — Mod B Kupon İmplantasyonu ve Flaş Tavlama
1. **Kupon Yazımı:** `f = %1,0` `²⁹Si / ²⁸Si` epitaksiyel kuponuna (`S5.4`, `5`-yonga deneme lotu) referans ızgarasında `64` aday yuva (`N = 1` sayılmış `³¹P⁺`/yuva) yaz; tüm atışları `ShotRecord` JSONL veritabanına aktar.
2. **ms Flaş Tavlama:** `600 °C / 10 dk` göç eşiği (`doi:10.1063/1.331355`) altında ms flaş tavlama uygula; ikiz kuponda donör aktivasyonunu (`≥ %70`) ve `σ_tavlama ≤ 0,5 nm` sınırını doğrula.

### Faz F — `MXC` Soğutma, `8`-Bobinli Mıknatıs (`1,50 T / 22,3 µT`) ve Yan SKY130 Testi
1. **Manyetik Harita (`R7` Fiziksel Doğrulama):** `8`-bobinli `S6.3` mıknatısını `1,500000 T`'ye rampa et (`I/I_c ≤ 0,212`); NMR/Hall ile yonga merkezinde **`ΔB/B ≤ 100 ppm`** (model `17,81 ppm`), `z_loc = −155 mm` `Nb (RRR>300)` + `Cryoperm-10` kabı içinde **`B_res ≤ 0,40 T`** (model **`22,3 µT`**, `B_perp ≤ 10 mT`) ve kontrollü quench (`≤ 65–100 K`, model `64,6 K`) doğrula (`Exp125`).
2. **Kriyo & `2`-Zincirli RF Okuma:** `MXC ≤ 20–25 mK`, `4 K` yükü `< 0,20 W`, `NbTiN` `Q_l = 800–1200`, `ton ≤ −100 dBm/kanal`, `SNR = 10` entegrasyon süresi `≤ 0,1 ms` (`0,0627 ms` model) ölç.
3. **İsteğe Bağlı `Exp33` Yan Kuponu:** `4 K` plakasındaki yan sokette SKY130 ileri-`V_B` ve çift-yönlü histerezis ölçümü (`C33-2/C33-5`).

### Faz G — Kapalı Çevrim II: İlk Sertifikalı Yazmaç ve `CellISA` Programı
1. **Ölç & Seç:** Aday yuvalarda Elzerman + ESR/ENDOR ile `{A_k}` hatlarını çıkar (`≤ ±200 Hz`); `src/machine_control/selector.py` (`AtlasSelector`) ile en az `1` (hedef `≥ 3`) `K=8` (veya `K=4`) yazmaç seç (`min_spacing ≥ 5 kHz`, Vandermonde `8/8`, `D0 ≤ 10⁻⁶`).
2. **Kalibre Et & `CellISA` Koştur (`Exp126` 32B Kilitli):** RF NMR bobininde **`10–15 kHz` Rabi genlik payı (`B₁ ≈ 1,2–1,8 mT`)** doğrulandıktan sonra `pulse_engine.py` / `grape_dd126.py` ile yazmaç-özgü 9-köşeli (`±400 Hz × ±%2`) iki-aşamalı 32B **`XY8`-GRAPE** sentezle (**`CPMG` yasak** — `+0,3245 / +0,6189` `XY8` üstünlüğü; **`N_total = 32–64`**, **`N = 32` global optimum `0,9260 / 0,9648`**, **`N = 128` DDRF duvarı yasak**; `ε ≤ 10⁻³`); `CellISA` üzerinden `Bell` (`0,9501`), `GHZ-4` (`0,9401`), `Grover-2` (`P(\|11⟩) = 0,9237`), `BitFlip-3` (`0,8878`) ve `QFT-3` (`0,8377`) programlarını koşturup tomografiyle **`Q_32D ≥ 0,85`** ve **`D0(17,5 s) ≤ 10⁻⁶`** (model `≤ 7,76×10⁻⁹`) doğrulayarak ilk fiziksel SHA-256 `ProgramCertificate` kaydını mühürle.

---

## 5. Zorunlu EHS ve Laboratuvar Güvenlik Protokolleri

### 5.1 `PH₃` (Fosfin) Toksik ve Piroforik Gaz Güvenliği — **KRİTİK ÖNCELİK**
Fosfin (`PH₃`) renksiz, solunumla hızla ölümcül ve saf hâlde piroforik bir gazdır (`OSHA PEL = 0,3 ppm` 8 saat TWA; `ACGIH TLV-STEL = 1,0 ppm`; `NIOSH IDLH = 50 ppm`) `{Literatür}`:
1. **Düşük Riskli Kaynak:** Sertifikalı seyreltik karışım (`%1–%5 PH₃` in `H₂`/`Ar`) veya sub-atmospheric adsorban tüp (**SDS/SAGE**) zorunludur.
2. **Muhafaza & Borulama:** SEMI S2 / NFPA 318 negatif basınçlı sürekli egzozlu çift-tüplü gaz kabini (`S1.6`), elektro-parlatılmış çift-cidarlı `316L VAR` metal VCR borulama (pirinç/elastomer yasak), otomatik `N₂` süpürme manifoldu.
3. **4-Nokta Sürekli Dedektör & SIL-2 PLC (`S7.4-04`):** Kabin, egzoz, kaynak başlığı ve solunum bölgesi dedektörleri (Alarm-1 `0,15 ppm` uyarı; Alarm-2 `0,30 ppm` `< 5 s` otomatik pnömatik silindir kapama + HV/plazma kesme + tahliye sireni; tümü UPS destekli).
4. **Arıtım (Scrubber):** Yağsız kuru ön-pompa çıkışı doğrudan sertifikalı kuru-reçine/ıslak scrubber'a (`< 50 ppb` çıkış) bağlanır; iki kişilik (buddy) çalışma ve erişilebilir SCBA zorunludur.

### 5.2 Yüksek Gerilim (`±5 kV` / `10–20 kV`), X-Işını, Kriyo, `1,50 T` Mıknatıs ve ESD
- **HV & X-Işını:** `+5 kV` anot ve `−5 kV` üst kolon gömleği akım sınırlı (`≤ 5 mA` kaynak, `≤ 1 mA` lensler), kapı interlock'lu ve LOTO + topraklama kancalıdır; devreye almada `< 0,5 µSv/h` Bremsstrahlung taraması yapılır.
- **Kriyo ODH & Quench:** Sürekli `O₂` monitörü (`< %19,5` uyarı, `< %18,0` tahliye), çift kademeli basınç tahliyesi, dış atmosfere yönlendirilmiş quench egzoz hattı (`T_hotspot = 64,6 K`, `R_dump = 1,563 Ω`).
- **Manyetik Alan (`1,50 T`):** `0,5 mT` (`5 Gauss`) hattı işaretli; kalp pili yasak bölgesi; yalnız `Ti`/`BeCu`/pirinç aletler.
- **Lazer & ESD:** İnterferometre kapalı ışın tüpü + OD gözlüğü; `< 50 V` HBM hassas IBIC/`NbTiN`/SET cihazları için ANSI/ESD S20.20 topraklı istasyon ve iyonlaştırıcı.

---

## 6. `M1` Go/No-Go Çıkış Kapıları (`G1`–`G8`, `Exp124–128` Kilitli)

> Aşağıdaki 8 kapının tamamı geçilmeden `M2` (`10²–10³` demetcikli MEMS prototip) yatırımına geçilmez.

| Kapı | Alt Sistem / Faz | Kilitli Kabul Eşiği (Go Kriteri) | Doğrulama Yöntemi | No-Go / Düzeltme Kuralı |
|---|---|---|---|---|
| **`G1`** | EHS & UHV (`Faz A–B`) | Tüm `PH₃`/HV/O₂/PLC interlock testleri `%100` PASS (`< 50 ppb`, `< 5 s`); UHV `≤ 10⁻⁸ mbar`; `σ_kademe ≤ 0,50 nm` RMS (`PT420` açıkken) | EHS tutanağı, RGA, interferometre PSD | Güvenlik kilidi geçmeden gaz/HV açılamaz |
| **`G2`** | İyon Kolonu (`Faz B–C`, `Exp124`) | Wien `m/q=31` ayrımı (`R_m ≥ 60`, hedef `120,6`); `HDA-HiRes` **`ΔE_FWHM ≤ 0,50 eV`** (hedef `0,453 eV`); `Arch-B` `WD = 0,250 mm`, `E_gap ≤ 12 MV/m` (`10,60 MV/m`), **`σ_spot ≤ 1,50 nm` @ `5 keV`** (hedef `1,428 nm`) | Wien taraması, RFA, Faraday `B_r`, bıçak-kenarı profili | `σ_spot > 1,6 nm` ise `HDA` yarık daraltılır veya `LMIS` opsiyonu değerlendirilir |
| **`G3`** | Soğuk-Ada IBIC (`Faz D`, `Exp127`) | `100 K` soğuk adada `LTC6268` CSA (`1,2 µs / 1 GΩ`): `C_det ≤ 1,5 pF` (hedef `0,5 pF`), **`ENC ≤ 30 e⁻`** (model `24,1 e⁻`), `P_false < 10⁻³ / 1 ms`, **`η ≥ 0,99` @ `5 keV`** (model `0,99936`), `blanker_gate` `1 ms` watchdog PASS | Test pulser, Lindhard `341,7 e⁻` PHA piki, FPGA sayım logu | RT'de çalıştırma yasak; `η < 0,99` ise kablo `< 5 cm` / `100 K` temas kontrol edilir (acil yedek `10 keV` `η=0,9998`) |
| **`G4`** | Aktivasyon & Difüzyon (`Faz E`) | ms flaş tavlama sonrası donör aktivasyonu `≥ %70` `{Varsayım}`, yüzey göçü yok (`σ_tavlama ≤ 0,5 nm`) | İkiz kupon SIMS / 4 K iletim | Göç görülürse ms flaş darbe süresi/enerjisi kısaltılır |
| **`G5`** | Mıknatıs & Kriyo (`Faz F`, `Exp125`) | `MXC ≤ 25 mK`, `B_z = 1,500000 T` (`ΔB/B ≤ 100 ppm`, model `17,8 ppm`), `z_loc = −155 mm` kalkanlı **`\|B_res\| ≤ 0,40 T`** (model **`22,3 µT`**, `\|B_perp\| ≤ 10 mT`), quench `≤ 100 K` (`64,6 K`), `NbTiN Q_l = 800–1200`, `SNR=10 ≤ 0,1 ms` | Termometri, NMR/Hall 3B harita, VNA `S21`, FAT quench | `\|B_res\| > 0,40 T` ise karşı-sargı akımı / `Nb` kalkan oturuşu ayarlanır |
| **`G6`** | Tek-Donor ESR/ENDOR & Seçim (`Faz G`) | `f = %1,0` Mod B kuponunda tek-atış okuma sadakati `≥ %95`, spektral belirsizlik `≤ ±200 Hz`, en az `1` (hedef `≥ 3`) `K=8` / `K=4` yazmaç seçimi | Elzerman + ESR/ENDOR + `AtlasSelector` | Verim `%26–69` bandının altına inerse `R1` bağ modeli deneysel spektrumla yeniden kalibre edilir |
| **`G7`** | GRAPE + `XY8` DD & `CellISA` (`Faz G`, `Exp126`) | RF bobin Rabi payı **`10–15 kHz` (`B₁ ≈ 1,2–1,8 mT`)**, zorunlu **`XY8` `N_total = 32–64`** (`N=32` optimum `0,9260/0,9648`, `N=64` `0,9209/0,9433`, `N=128` ve `CPMG` yasak), `ε ≤ 10⁻³`, **`D0(17,5 s) ≤ 10⁻⁶`** (model `≤ 7,76×10⁻⁹`), **`Q_32D ≥ 0,85`**, `CellISA` Bell/GHZ-4/Grover-2/BitFlip-3/QFT-3 SHA-256 sertifikası | 32B durum tomografisi + `ProgramCertificate` JSONL + `XY8` eksen testi | `Q < 0,85` ise **`N = 128`'e çıkılmaz** (`sp_ovl=0,0972` DDRF duvarı!); `N = 32` optimumuna dönülür, `10–15 kHz` RF payı ve `ε ≤ 10⁻³` kalibrasyonu sıkılaştırılır |
| **`G8`** | Maliyet & 6-RFQ Bütçe Kapısı (`Exp128`) | `M1` faturaları (`~$2,19M` ref.) + 6-RFQ bağlayıcı teklifleriyle (`%92,8` BOM varyansı) güncellenen `Exp128` `M3` Program `P50 ≤ $50M` (`P95 ≤ $100M` sert sınır içi) | 6-RFQ uzlaştırması + `run_exp128.py` + `BUTCE_DURUMU.md` | `> $50M` ise gerekçe `BUTCE_DURUMU.md`'ye işlenir; `> $100M` ise ölçek/`4–8 GHz` bandı/`1 K` filo revizyonu zorunludur |
