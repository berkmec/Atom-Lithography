# `M1` Fiziksel Laboratuvar Prototipi Tasarım ve Kurulum Planı (`M1_PROTOTYPE_BLUEPRINT`)

**Sürüm:** `v6.0` (Tam `v6.0` Modüler Ölçekleme, `qLDPC` & Canlı IBM QPU Kilidi — `Exp124–146`, `CAD v6.0`, `Q16.16` BOED-FPGA & `CellISA v4.0` + `auto_recal.py` + `ibm_marrakesh` canlı kontrol doğrulaması, `S5.5` `1530,1 K` + `S5.6` LT-MBE Rota C, `S6.11/S6.5` Cryo-MUX/TWPA, `BOM_DETAILED v6.0` [`M1 Base` & `M3 Base` korundu + `Option-Q`/`Option-HPC`], `9-RFQ`, `252/252` `pytest` — 2026-11-23).  
**Dayanak:** [DESIGN.md](DESIGN.md) (`v6.0`), [MODULAR.md](MODULAR.md) (`v6.0-ICD`), [BOM_DETAILED.csv](BOM_DETAILED.csv) (`v6.0`, `174` parça), [BOM_ENGINEERING.md](BOM_ENGINEERING.md) (`v6.0`), [RFQ_SPECIFICATIONS.md](RFQ_SPECIFICATIONS.md) (`9-RFQ`), [LITERATURE.md](LITERATURE.md), [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md) (`v6.0`), `research/atom_lithography_machine/cad/cad_verification.json` (`CAD v6.0`: `199` parça, `1.108,14 kg`, `0/19.701` çakışma, `40/40` boşluk), `results/exp124..146*`.

> **Epistemik Sınır ve Amaç:** Bu belge, `M0` (`252/252` `pytest`, `28/28` dosya) aşamasından ilk fiziksel laboratuvar gösterimine (**`M1 Base`**) geçişin eksiksiz mühendislik planıdır:
> - **Silikon `³¹P` fabrikasyon & `M1–M4` donanım kurulumu:** `M0` tasarım & sayısal fizibilite aşamasındadır (**`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`**).
> - **Kontrol yazılımı (`CellISA v4.0 → OpenQASM 3.0`), `Echo/XY4` DD, `d=3` sendrom dekoderi ve bit-kesin `Q16.16` BOED:** **Gerçek `156`-kübitlik `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, `16 PUB × 4.096 shot`, `32,54 s`) bulut QPU üzerinde canlı olarak doğrulanmıştır** (`{Canlı-Donanım-IBM-QPU}`, sıfır gizli sızıntı); bu sayede `M1` yazılım yığını silikon laboratuvarı kurulmadan önce gerçek kuantum donanımında sınanmıştır.

---

## 1. `M1 Base` (`v6.0`) Görev Tanımı, Bütçe Koruması ve Modüler Yükseltme Yolu
- **Tek Cümlelik Hedef:** Seyreltik epitaksiyel `²⁹Si` banyosu (`f = %1,0` baz ve **`f* = %1,5 + 2 MV/m`** Stark-destekli hedef, Mod B — donör saçılmasından etkilenmeyen baz mod, `Exp124 CD8` & `Exp136`) taşıyan `²⁸Si` test kuponları üzerinde, tek-demet `10→5 keV` sayılmış `³¹P⁺` implantasyonu + `100 K` soğuk-ada IBIC + **`S5.5` `808 nm / 1,0 ms / 1530,1 K` (`43,49 J/cm²`) küme-temizleyici flaş tavlama** (`Exp139`) + **`S5.6` `8 nm` LT-MBE (`345 °C`) + `350 °C` `FG/H₂` Rota C pasivasyonu** (`S_ε = 0,390 µeV/√Hz`, `Exp139`) + **`S6.9` ayrıştırılmış `PT420`** (`σ_stage = 0,1024 nm`, `Exp133`) + `MXC` (`~20 mK`, `1,500000 T`) **`Q16.16` BOED-FPGA & TWPA/Purcell** (`Exp132/140`) + **`CellISA v4.0`** (`20` komut) + **`auto_recal.py`** ile:
  1. **En az bir (hedef: `≥ 3`) sertifikalı `K=8` (veya evrensel `K=4` altküme) çekirdek-spin yazmacını fiziksel olarak doğrulamak ve `CellISA v4.0` (`20` komut) + `auto_recal.py` (`4/4` arıza kurtarma) üzerinden `Bell`/`GHZ-4`/`BitFlip-3`/`QFT-3` ve tek-zincir `MUX_READOUT` / sendrom döngüsü doğrulamasını koşturmak** `[DESIGN.md v6.0 §10 | M1]`,
  2. **`G6b` (`Exp129/136` Risk `R1`) deneysel `ENDOR` ölçümüyle `f = %1,0` ve `f* = %1,5 + 2 MV/m` kuponlarında gerçek çalışma verimini (`Exp136`: `%52,75` / `%77,50` → `M4 %99,88`; `Exp144` `N_cand = 8` `qLDPC` `%99,64` blok / `%99,94` `108L` yonga verimi) ve `S5.6` Rota C yük-gürültüsü düşüşünü (`S_ε ≤ 0,40 µeV/√Hz`) laboratuvarda kanıtlayarak `D3` GRAPE + tek-kriyostatlı `108L` `qLDPC` ölçek yolunu (`$63.827/L_sys`) kilitlemek.**
- **Finansal ve Stratejik Mantık (`Exp128 v6.0` + `BOM_ENGINEERING.md v6.0`):**
  - **`M1 Base` nominal donanım maliyeti DEĞİŞTİRİLMEDEN KORUNMUŞTUR:** **`$2.466.120`** (`$1.454.996–$4.400.788`; `M3 Base` `$5.247.800` toplamının `%47,0`'ı, `M3 v6.0 Full` `$5.547.800` toplamının `%44,5`'i).
  - **Modüler `v6.0` Yükseltme Yolu (`0` Çift Sayım, `$0,00` Köprü):**
    - `M1 Base`: **`$2.466.120`** (gün-1 silikon prototip; `v6` eklentileri hariç)
    - `M3 Pilot` (`256`-hücre): **`$4.790.400`**
    - `M3 Base` (`1.024`-hücre, `167` parça, `1.034,94 kg`, `P(Prog>$100M) = %4,37`): **`$5.247.800`**
    - **`+ Option-Q`** (`S1.7-01` `S1-Multi` `³¹P/¹²¹Sb/¹⁶⁷Er` + `S9.4-01..03` `50 Ω ↔ 3 kΩ` `qRAM`/`1550 nm` fiber, **`+$168.000 / +9,20 kg`**): **`$5.415.800`**
    - **`+ Option-HPC`** (`S9.HPC-01..03` `4U` `100G` RoCEv2 RDMA QEC dekoderi, **`+$132.000 / +64,00 kg`**): **`$5.379.800`**
    - **`M3 v6.0 Full`** (`Option-Q + Option-HPC`, `174` BOM / `199` CAD parça, **`1.108,14 kg`**, `P50 = $36,25M`, **`P(Prog > $100M) = %4,92 < %5`** [FOAK `%6,90`]): **`$5.547.800`**
  - **Yüksek Yatırım Koruması:** `M1 Base` donanımının **`~%84`'ü (`~$2,08M`)** doğrudan `M3 Base` ve `M3 v6.0 Full` gövdesine taşınır; üstelik `Exp144` **`[[144,12,12]]` `qLDPC` mimarisi `108L` mantıksal kübiti tek bir `LD400/PT420` kriyostata sığdırdığından**, `M1`'de satın alınan `20 mK` DR + `S6.9` + `1,50 T` mıknatıs + `S5.6` MBE çekirdeği doğrudan `100L+` hata-toleranslı kuantum bilgisayara yükseltilebilir!

---

## 2. `M3 v6.0 Full` → `M1 Base` Alt-Sistem İndirgeme Tablosu (`Exp128 v6.0` & `CAD v6.0` Kilitli)

| Alt Sistem | `M3 v6.0 Full` (`$5.547.800` Nom) | `M1 Base` Prototipi (`$2.466.120` Nom) | `M1` Payı | Kilitli Fizik / Mühendislik Şartnamesi (`Exp124–146` & `CAD v6.0`) |
|---|---|---|---:|---|
| **`S1` Kaynak, Kolon & `S1.7` Multi** | Çift hat (`³¹P⁺/²⁹Si⁺`) + `Option-Q` `S1.7-01` `S1-Multi` (`+$68k, 4,8 kg`), `23` parça, **`$484.000`** *(Base `$416k`)* | **Tek hat (`³¹P⁺`, Mod B)** duoplazmatron + `PH₃` kabini + Wien + `HDA-HiRes` + `10→5 keV` kolon (**`$319.750`**; `S1-Multi` sonradan CF40 porttan takılır) | `%66,1` *(`%76,9` Base)* | Kolon `562,66 mm / Ø110 mm / 25,92 kg` (`CAD v6 S1: 30,78 kg`); Wien `0,45 T, R_m=120,6`; **`HDA-HiRes`** (`0,453 eV`); wafer `0 V`, üst gömlek `−5 kV`, anot `+5 kV` (`Exp124/142`) |
| **`S2` Yazma Kafası** | **`32×32 = 1.024` eş-adımlı `0,50 mm`** MEMS/`Arch-B`, `18` parça, `$775.500` | **Tek-delikli mikro-apertür + tek kanal blanker + tek eksenli `Arch-B` lens** (**`$147.750`**) | `%19,1` | **`Arch-B`**: `WD = 0,250 mm`, `E_gap = 10,60 MV/m`, `C_c = 2,660 mm`, `σ_spot = 1,428–1,532 nm`; `v5/v6` birleşik **`σ_tot = 3,588 nm (10 ms) / 3,631 nm (15 ms)`** (`Exp124/139/141`) |
| **`S3` Soğuk-Ada IBIC** | `16×8` kanal vakum-içi CSA + çok-karolu FPGA, `14` parça, `$224.000` | **`1–2` adet 8-kanallı `100 K` soğuk-ada IBIC kartı (`src/board/`) + 1 adet FPGA kartı (`blanker_gate.v`)** (**`$88.550`**) | `%39,5` | **`Exp127` KİLİDİ:** `100 K` `LTC6268` CSA (`Cf=0,25 pF, Rf=1 GΩ`) + `ADA4817-1` (`1,2 µs, ×50`) + `DAC8568` + `TLV3501` (`204` parça, `0` ERC): **`ENC = 24,1 e⁻`**, **`η(5 keV, 0,5 pF) = 0,99936`**, `C_det ≤ 1,5 pF` |
| **`S4` Konum & İnterf.** | Granit + `VC-E` (`VC-G` ops.) + `6-DOF` piezo + 3-eksen interferometre (`Zerodur/Invar-36`), `17` parça, `$253.000` | Aynı yalıtım & `6-DOF` UHV piezo + 2/3-eksen `pm` interferometre + `Zerodur/Invar-36` kaide (**`$233.920`**) | `%92,5` | **`Exp133` kilitli:** `43,57 Hz` PID + `25 dB` FF → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**, **`σ_thermal = 0,0283 nm`** (`20 mK`) |
| **`S5` UHV, `S5.5` `1530,1 K` & `S5.6` MBE** | `s=0,5` UHV (`34,86 L`) + `S5.5` `1530,1 K` (`$95k`) + `S5.6` LT-MBE (`$95k`, `22,4 kg`) + `25`-yonga epi, `24` parça, **`$433.000`** | Aynı UHV + `S5.5` `1530,1 K` (`$66,5k`) + **`S5.6` tam yerinde `8 nm` LT-MBE + `FG/H₂` (`+$95k`)** + `f=%1,0` & `f*=%1,5` lotu (**`$358.300`**) | `%82,7` | **`Exp130/139` (`R6` kapalı):** `v4` `1440 K` (`+1,318 nm` gizli TED!) yasaklandı → **`S5.5` `1530,1 K` (`43,49 J/cm²`, `$0` HW, `%99,99` `{311}` temizliği, `σ_anneal = 0,430 nm`)** + **`S5.6` `345 °C` MBE + `350 °C` `FG/H₂` Rota C (`S_ε = 0,390 µeV/√Hz`, `p_ff = %97,70`)** |
| **`S6` Kriyo, `S6.9`, Mıknatıs, `M4` & `S6.11` MUX** | `20 mK` DR + `PT420` + `S6.9` + `1,5 T` mıknatıs + `56` zincir + `S6.10` (`$171k` net) + `S6.11` `32`-hat TWPA/ZU48DR (`$629,2k`), `42` parça, **`$2.794.100`** | **Aynı `20 mK` DR (`$720k`) + `PT420` + `S6.9` (`$68k`, ZORUNLU) + `1,50 T` mıknatıs (`$185k`) + `2` RF zinciri + `S6.11` `1× ZU48DR` + `1` test TWPA/Purcell/HEMT zinciri (`+$46,85k`)** (**`$1.171.150`**) | `%41,9` | `1,500000 T ± 17,8 ppm`, `22,3 µT`, `64,6 K` (`Exp125`); `Q16.16` `2,336 µs/adım`, `N_mux* = 32` (`F_RO = %99,61`, `625×` Purcell, `Exp140`); **`D3` GRAPE (`p_2q = %0,337–0,395`) + `[[144,12,12]]` `qLDPC` aynı DR'de `120L` taşır (`Exp143/144`)** |
| **`S7–S8` Kontrol, `CellISA v4.0` & `auto_recal`** | `2×` GPU + AWG + SKY130 MPW (`S7.1-04` `$0` ikame), `14+9` parça, **`$204.200`** | `1×` GPU + `1×` AWG + `1×` EMI kabin + **`machine_control` v4.0 (`CellISA v4.0` `20` op + `auto_recal.py` + `cloud_qpu_bridge.py`)** (**`$104.450`**) | `%51,1` | **Canlı `156Q` `ibm_marrakesh` (`dc1tdo2nj2vs73dfrfl0`):** Bare `0,3325` → Echo `0,9224` → XY4 `0,9280`, Bell `0,9733`, `d=3` `5,16×/7,83×`, `Q16.16 BOED` `120,11 kHz` (`1,6 Hz` vs FP64); `auto_recal` `4/4 PASS`; **`252/252` `pytest`** |
| **`S9` Sarf, Yedek & `v6` Opsiyonlar** | Yedekler (`$148k`) + **`Option-Q` `S9.4` (`+$100k, 4,4 kg`)** + **`Option-HPC` `S9.HPC` (`+$132k, 64,0 kg`)**, `13` parça, **`$380.000`** | Kalibrasyon kuponları + `PH₃` sarfı + tek-eksen yedekleri (**`$42.250`**; `Option-Q` ve `Option-HPC` `M3/M4` aşamasında tak-çıkar eklenir) | `%11,1` *(`%28,5` Base)* | `Option-Q`: `8.403×–25.122×` `qRAM` ömür (`+0,78 µW @ 20 mK`); `Option-HPC`: `qLDPC 108L 2,32 µs < 2,62 µs` (`2.195 W`, `0 W` kriyo) |

---

## 3. `M1 Base` (`v6.0`) Fiziksel Mimari ve Sinyal Akışı (`Exp124–146` & `CAD v6.0` Kilitli)

```text
[S1.6: PH3 Negatif Basınçlı Gaz Kabini (SDS/Seyreltik) + Kuru/Islak Scrubber]
        │ (çift-cidarlı 316L VCR, 4x dedektör, <5 s pnömatik kesme)
        ▼
[S1.1: Duoplazmatron (+5,0 kV anot; üst gömlek −5,0 kV) + ops. CF40 S1.7 S1-Multi]
        │ (10 keV çıkarım; toplam kolon 562,66 mm [z_CAD 500,25..1062,66 mm], max OD 110 mm)
        ▼
[S1.4 Kondansör] → [S1.2 Wien (0,45 T, R_m=120,6)] → [S1.5 HDA-HiRes (ΔE_FWHM=0,453 eV)]
        │
        ▼
[S1.6 Transfer] → [S2.1 Tek Mikro-Apertür] → [S2.2 Blanker (100 MHz FPGA, blanker_gate.v)]
        │
        ▼
[S2.3 Arch-B Yavaşlatıcı Mini-Lens (WD=0,250 mm, E_gap=10,60 MV/m, Cc=2,660 mm)]
        │ (5,000 keV 31P+ tek iyon → alansız 0 V wafer, σ_spot=1,428–1,532 nm, σ_tot=3,588–3,631 nm)
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S5.1: s=0,5 UHV Ana Oda (R_iç=182 mm, 34,86 L, ≤10⁻⁸ mbar) — VC-E Masa     │
│  • S4.3: 6-DOF UHV Piezo (43,57 Hz PID + 25 dB FF → σ_stage=0,1024 nm)     │
│          + Zerodur/Invar-36 Kaide (σ_thermal=0,0283 nm @ 20 mK, Exp133)    │
│  • Test Kuponu (f=%1,0 & f*=%1,5 29Si/28Si Epi, 0 V) + BeCu/Au IBIC Halka  │
│  • S3.2 Soğuk-Ada (100 K) 8-Kanallı IBIC (204 parça, 0 ERC, Exp127):       │
│      LTC6268 (0,25 pF, 1 GΩ) → ADA4817-1 (1,2 µs) → DAC8568 + TLV3501      │
│      [ENC=24,1 e⁻, η(5 keV, 0,5 pF)=0,99936, C_det≤1,5 pF marjı]           │
│  • +Y CF63 S5.5 Flaş Portu (808 nm / 1,0 ms / 1530,1 K, 43,49 J/cm² ± %5)  │
│  • Üst CF100 S5.6 LT-MBE (22,4 kg, 0 µW kriyo, %0 akış cezası):            │
│      8 nm 28Si @ 345 °C + 350 °C FG/H2 Rota C → S_ε=0,390 µeV/√Hz, %97,7  │
└───────┬────────────────────────────────────────────────────────────────────┘
        │ (In-line RT load-lock 1530,1 K flaş + S5.6 MBE Rota C [σ_anneal=0,430 nm, f_act=%99,92])
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S6.8/S6.1/S6.9/S6.11: Seyreltme Kriyostatı (MXC ~20 mK) + Ayrış. PT420     │
│  • S6.9 PT420 Ayrıştırma (ZORUNLU, Exp133 CFG4): 500 mm uzak valf +        │
│      600 mm esnek He + 2.000 N/m körük + 4× OFHC Cu örgü (ΔT=3,7 mK)       │
│  • S6.3: 8-Bobinli NbTi Mıknatıs (1,500000 T ± 17,8 ppm, quench 64,6 K)    │
│  • z_loc = −155 mm Nb (RRR>300) + Cryoperm-10 → B_res = 22,3 µT (Exp125)   │
│  • 2 RF Zinciri + S6.11 Test TWPA/Purcell/HEMT (Purcell 625×, F_RO=%99,61) │
│  • [M3/M4 Opsiyonel Portlar: S9.4 Option-Q qRAM (+0,78 µW) & S9.HPC RDMA]  │
│  • MW (ESR) + RF (ENDOR) + E_z = 2 MV/m Stark Kapısı ◄── ZU48DR + AWG     │
└───────┬────────────────────────────────────────────────────────────────────┘
        ▼ (Q16.16 BOED-FPGA 2,336 µs/adım + G6b ENDOR R1 & Rota C S_ε ölçümü)
[M8: src/machine_control v4.0 (CellISA v4.0 20 op + auto_recal + cloud_qpu_bridge)]
```

> **Kritik Mühendislik Notları (`Exp127` + `Exp133` + `Exp139` + `Exp145`):**
> 1. **`100 K` Soğuk-Ada IBIC (`Exp127`) & `S6.9` `PT420` (`Exp133`):** RT `200 ns` IBIC (`η=0,097`) ve rijit `PT420` (`2.052 nm`) gün-1 kırmızı çizgilerdir; `100 K / 1,2 µs / 1 GΩ` IBIC ve `S6.9 CFG4` zorunludur.
> 2. **Gizli TED & `1530,1 K` Flaş (`Exp139 EP5`):** Eski `v4.0` `1440 K` flaş `%13,6` artık `{311}` kümesi bırakarak arka-uç MBE sırasında `+1,318 nm` gizli TED (`3,995 nm` FAIL!) ürettiği için yasaklanmıştır; **`S5.5` `1530,1 K / 43,49 J/cm²`** (`$0` HW, `%99,99` temizlik, `σ_anneal = 0,430 nm`) zorunludur.
> 3. **Canlı QPU Ön-Doğrulama (`Exp145`):** `M8` kontrol yığını (`CellISA v4.0`, `Q16.16` BOED, `Echo/XY4` DD, `d=3` MWPM) silikon kuponundan önce gerçek `156Q` `ibm_marrakesh` işlemcisinde canlı doğrulandığından yazılım devreye alma riski minimuma indirilmiştir.

---

## 4. Adım-Adım Kurulum, Hizalama ve Kalibrasyon Prosedürü (`Faz A` – `Faz G`)

### Faz A — Temel Altyapı, UHV (`CAD v6.0`) ve `S6.9` `PT420` Titreşim + Termal Ayrıştırma (`Exp133`)
1. **Zemin & `S6.9` `PT420` Kurulumu:** `VC-E` (`VC-G` ops.) aktif optik masa, `Zerodur/Invar-36` kaide (`20 mK` → `σ_thermal = 0,0283 nm`) ve `6-DOF` UHV piezo (`S4.3`) kurulur; `PT420` `500 mm` uzak valf + `600 mm` He + `2.000 N/m` körük + `4×` OFHC Cu örgü (`ΔT = 3,7 mK`) üzerinden ayrıştırılır.
2. **Servo & Harmonik FF:** `43,57 Hz` PID (`PM ≥ 45°`, `GM ≥ 6 dB`) + `25 dB` harmonik FF ile **`σ_stage ≤ 0,25 nm` (`0,1024 nm`)** ve **`σ_pointing ≤ 0,25 nm` (`0,1473 nm`)** kanıtlanır.
3. **UHV, `S5.5` & `S5.6` LT-MBE Montajı (`CAD v6.0` `199` parça, `1.108,14 kg` Full / `1.034,94 kg` Base, `0/19.701` çakışma, `40/40` boşluk):** `s=0,5` UHV oda (`34,86 L`), `+Y` CF63 `S5.5` safir pencere ve üst CF100 `S5.6` LT-MBE (`22,4 kg`) `He` kaçak testinden (`≤ 10⁻¹⁰ mbar·L/s`) geçirilip `≤ 10⁻⁸ mbar` (`MBE < 5×10⁻¹⁰ mbar`) taban basıncı alınır; ilerideki `Option-Q` (`S1.7` CF40 & `S9.4` OVC port) ve `Option-HPC` (`+X` `60 mm` servis koridoru) boşlukları korunur.

### Faz B — `PH₃` Devreye Alma, Kaynak, Wien ve `HDA-HiRes` Süzgeç Kalibrasyonu
1. **EHS İmzalı Ön Koşul:** §5.1 `PH₃` güvenlik testleri (4 dedektör, `< 5 s` kesme, scrubber) imzalanmadan gaz açılmaz.
2. **İnert Gaz & Kütle Ayrımı:** Önce `Ar/N₂` plazmasıyla `+5 / −5 kV` HV (`ΔV/V ≤ 10⁻⁴`), sonra `PH₃` ile Wien (`0,45 T, V_p = 1.348 V`) `m/q = 31/32` (`dx = 0,785 mm, R_m = 120,6`) ayrımı doğrulanır.
3. **`HDA-HiRes` Enerji Süzgeci:** `R₀ = 40 mm, E_pass = 100 eV, slit = 0,35 mm` ayarında **`ΔE_FWHM ≤ 0,50 eV`** (`0,453 eV`) ve `B_r` doğrulanır (`Exp124`).

### Faz C — `Arch-B` `10→5 keV` Yavaşlatma Lensi, Blanker ve Demet Nokta Metrolojisi
1. **Blanker Hız Testi:** FPGA `blanker_gate.v` (`100 MHz`) ile sönüm oranı `> 10⁴`, anahtarlama `< 100 ns`.
2. **`Arch-B` Çalışma Mesafesi & Profil:** Wafer `0 V`, **`WD = 0,250 mm`** (`E_gap = 10,60 MV/m`) bıçak-kenarı profiliyle **`σ_spot ≤ 1,50 nm`** (`1,428 nm @ 10 ms`; `1,532 nm @ 15 ms`) doğrulanır (`Exp124`).
3. **Kafa–Kademe Matrisi:** Kalıntı `< 0,25 nm` → birleşik **`σ_tot = 3,588–3,631 nm ≤ 3,80 nm`**.

### Faz D — `100 K` Soğuk-Ada IBIC Kalibrasyonu ve Sayılmış Tek-İyon İmplantasyonu
1. **`100 K` Soğuk-Ada CSA:** `src/board/` 8-kanallı kartı `100 K` adaya bağla (`C_par < 0,15 pF`, `τ = 1,2 µs, R_f = 1 GΩ, ×50`): **`ENC ≤ 25–30 e⁻`** (`24,1 e⁻ @ 0,5 pF`), `P_false < 10⁻³ / 1 ms` (`2,59×10⁻⁴`).
2. **`5 keV ³¹P⁺` Tek-İyon Sayımı:** Lindhard `341,7 e⁻` pikiyle hizala; `blanker_gate.v` kapalı çevriminde **`η ≥ 0,99`** (`0,99936 @ 0,5 pF`, `0,9906 @ 1,5 pF`) kanıtla (`Exp127`).

### Faz E — Mod B Kupon İmplantasyonu, `S5.5` `1530,1 K` Flaş & `S5.6` LT-MBE Rota C (`Exp130/139`)
1. **Kupon Yazımı:** `f = %1,0` ve **`f* = %1,5`** (`Exp136`) kuponlarına `≥ 64` (tercihen `128`) aday yuva yaz (`N = 1` sayılmış `³¹P⁺`/yuva).
2. **`S5.5` `808 nm / 1,0 ms / 1530,1 K` Küme-Temizleyici Flaş (`Exp139`, `$0` HW):** Fırın, RTA ve eski `v4.0` `1440 K` reçetesi **yasaktır**. İn-line RT load-lock konumunda (`MXC < 1 K` + UHV perde kilitli) `+Y` CF63 safir pencereden (`1530,1 K` LIDT marjı **`8,96×`**) **`808 nm / 1,0 ms / F = 43,49 J/cm² ± %5`** (**`T_peak = 1530,1 K`**, arka yüz `608,3 K`, `%99,99` `{311}` temizliği) uygula.
3. **`S5.6` Yerinde `8 nm` LT-MBE & `FG/H₂` (Rota C, `Exp139`):** Üst CF100 `S5.6` MBE haznesinde **`345 °C`**'de **`8,0 ± 1,0 nm`** `²⁸Si` kapak büyüt (`R_q ≤ 0,20 nm`), ardından **`350 °C` `FG/H₂`** uygula. İkiz kuponda **`f_act ≥ %85`** (`%99,92`), **`σ_anneal ≤ 0,50 nm`** (`0,430 nm`), kayıp `< %1` (`%0,079`), `σ_iso < 0,1 nm` (`0,0515 nm`) ve **`S_ε ≤ 0,40 µeV/√Hz`** (`0,390 µeV/√Hz`, `p_ff = %97,70`) doğrula.

### Faz F — `MXC` Soğutma, `8`-Bobinli Mıknatıs (`1,50 T / 22,3 µT`) & `S6.11` TWPA/Purcell Testi
1. **Manyetik Harita (`R7`):** `B_z = 1,500000 T ± 100 ppm` (`17,81 ppm`), `z_loc = −155 mm` kalkan içinde **`B_res ≤ 0,40 T`** (**`22,3 µT`**), quench `≤ 100 K` (`64,6 K`) doğrula (`Exp125`).
2. **Kriyo & Tek-Zincir `S6.11` TWPA/Purcell (`Exp140`):** `MXC ≤ 25 mK`, `S6.9` Cu örgü `ΔT ≤ 10 mK` (`3,7 mK`), `Purcell ≥ 100×` (`625×`), `τ_RO = 2,0 µs` tek-atış okuma sadakati **`F_RO ≥ %99,0`** (`%99,61`, `N_mux* = 32` mimari kanıtı).
3. **İsteğe Bağlı `Exp33` Yan Kuponu:** `4 K` plakasındaki yan sokette SKY130 ileri-`V_B` histerezis ölçümü.

### Faz G — Kapalı Çevrim II: `Q16.16` BOED-FPGA, `G6b` `ENDOR` (`f* = %1,5 + 2 MV/m`), `CellISA v4.0` & `auto_recal` (`Exp126/132/136/140/145`)
1. **`Q16.16` BOED-FPGA (`Exp132/140/145`):** `ZU48DR` (`fpga_boed_dsp.py`) üzerinde adım gecikmesi `< 25 µs` (**`2,336 µs`**), FP64 paritesi `abs(ΔRMS) < 1,0 Hz` (**`0,0502 Hz`**; ayrı canlı `ibm_marrakesh` Ramsey `Δf` paritesi **`1,6 Hz < 500 Hz`**), ortalama yuva `≤ 80 ms` (`41,03 ms`), `RMS ≤ 150 Hz` (`72,67 Hz`), `FNR ≤ %1`, `FPR ≤ %0,5`.
2. **`G6b` — Risk `R1` `ENDOR` & `E_z = 2 MV/m` Stark Verim Kapısı (`Exp129/136/144`):** `≥ 64` donorda **`p_work(f*=%1,5 + 2 MV/m) ≥ %50`** (`Exp136`: `%77,50` / DDRF `%54,00` → `M4 %99,88`; `Exp144` `N_cand = 8` **`%99,64` `qLDPC` blok verimi**) ve **`p_work(f=%1,0) ≥ %30`** (`%52,75`) kanıtlanır. Altında kalınırsa `f* = %2,0` (`XY8 T₂e = 10,8 ms`) veya `K=4` revizyonu uygulanır.
3. **`XY8`-GRAPE, `CellISA v4.0` & `auto_recal.py` (`Exp126/143/145`):** RF payı `10–15 kHz`, zorunlu **`XY8` `N_total = 32–64`** (`N=32` optimum, `N=128` ve `CPMG` yasak), **`CellISA v4.0`** (`20` komut: `+ QRAM_SWAP, QLDPC_ROUND, AUTO_RECAL`) ile `Bell/GHZ-4/Grover-2/BitFlip-3/QFT-3` koşturulup `Q_32D ≥ 0,85`, `D0(17,5 s) ≤ 10⁻⁶` ve `auto_recal` 4-arıza kurtarma testi doğrulanarak ilk fiziksel SHA-256 `ProgramCertificate` mühürlenir.

---

## 5. Zorunlu EHS ve Laboratuvar Güvenlik Protokolleri

### 5.1 `PH₃` (Fosfin) Toksik ve Piroforik Gaz Güvenliği — **KRİTİK ÖNCELİK**
Fosfin (`PH₃`) renksiz, solunumla hızla ölümcül ve saf hâlde piroforiktir (`OSHA PEL = 0,3 ppm`, `TLV-STEL = 1,0 ppm`, `IDLH = 50 ppm`) `{Literatür}`:
1. **Düşük Riskli Kaynak:** Sertifikalı seyreltik karışım (`%1–%5 PH₃`) veya sub-atmospheric adsorban tüp (**SDS/SAGE**) zorunludur.
2. **Muhafaza & Borulama:** SEMI S2 / NFPA 318 negatif basınçlı çift-tüplü gaz kabini (`S1.6`), çift-cidarlı `316L VAR` VCR borulama, otomatik `N₂` süpürme.
3. **4-Nokta Dedektör & SIL-2 PLC (`S7.4-04`):** `0,15 ppm` uyarı, `0,30 ppm` `< 5 s` otomatik silindir kapama + HV/plazma kesme + tahliye sireni (UPS destekli).
4. **Arıtım (Scrubber):** Kuru ön-pompa çıkışı doğrudan scrubber'a (`< 50 ppb`) bağlanır; iki kişilik çalışma ve SCBA zorunludur.

### 5.2 Yüksek Gerilim (`±5 kV`), `S5.5` Sınıf-4 Lazer, `S5.6` `FG/H₂`, Kriyo, `1,50 T` Mıknatıs ve ESD
- **HV & X-Işını:** `+5 / −5 kV` akım sınırlı (`≤ 5 mA` / `≤ 1 mA`), kapı interlock, LOTO + topraklama kancası, `< 0,5 µSv/h` Bremsstrahlung taraması.
- **`S5.5` Sınıf-4 `808 nm` `1530,1 K` Flaş Lazeri:** Kapalı ışın tüpü, `OD ≥ 7 @ 808 nm` gözlük, `MXC < 1 K` + UHV perde kilidi, `10 µs` pirometre aşırı-sıcaklık kesmesi (**`T > 1580 K`**, `1530,1 K` hedefinin `+50 K` üstü, `1687 K` ergimenin `−107 K` altı).
- **`S5.6` LT-MBE & `FG/H₂`:** Sertifikalı yanıcı-olmayan `%5 H₂ / %95 N₂` karışımı, egzoz seyreltmesi, `345–350 °C` termokupl kesmesi.
- **Kriyo ODH, `1,50 T` Mıknatıs & ESD:** `O₂` monitörü (`< %19,5` / `< %18,0`), quench tahliyesi (`64,6 K`), `5 Gauss` sınırı, ANSI/ESD S20.20 istasyonu.

---

## 6. `M1 Base` (`v6.0`) Go/No-Go Çıkış Kapıları (`G1`–`G8`, `G6b` Dahil — `Exp124–146` Kilitli)

> Aşağıdaki 9 kapının tamamı geçilmeden `M2` (`10²–10³` demetcik MEMS) ve `M3 v6.0 Full` (`Option-Q` + `Option-HPC` + `108L` `qLDPC`) yatırımına geçilmez.

| Kapı | Alt Sistem / Faz | Kilitli Kabul Eşiği (`v6.0` Go Kriteri) | Doğrulama Yöntemi | No-Go / Düzeltme Kuralı |
|---|---|---|---|---|
| **`G1`** | EHS, UHV & `S6.9` `PT420` (`Faz A–B`, `Exp133`, `CAD v6.0`) | Tüm EHS/PLC interlock `%100` PASS; UHV `≤ 10⁻⁸ mbar`; `CAD v6.0` `0/19.701` çakışma (`40/40`); `CFG4` **`σ_stage ≤ 0,25 nm`** (`0,1024 nm`), **`σ_pointing ≤ 0,25 nm`** (`0,1473 nm`), **`σ_thermal ≤ 0,10 nm`** (`0,0283 nm`) | EHS tutanağı, RGA, interferometre PSD, PID Bode (`PM≥45°`) | Kilit geçmeden gaz/lazer/HV açılamaz; `σ_stage > 0,25 nm` ise körük/örgü/FF sıkılaştırılır |
| **`G2`** | İyon Kolonu (`Faz B–C`, `Exp124`) | Wien `R_m ≥ 60` (`120,6`); `HDA-HiRes` **`ΔE_FWHM ≤ 0,50 eV`** (`0,453 eV`); `Arch-B` `WD = 0,250 mm`, `E_gap ≤ 12 MV/m`, **`σ_spot ≤ 1,50 nm` @ `5 keV`** (`1,428 nm`) | Wien taraması, RFA, Faraday `B_r`, bıçak-kenarı profili | `σ_spot > 1,6 nm` ise `HDA` yarık daraltılır veya `LMIS` değerlendirilir |
| **`G3`** | Soğuk-Ada IBIC (`Faz D`, `Exp127`) | `100 K` `LTC6268` CSA (`1,2 µs / 1 GΩ`): `C_det ≤ 1,5 pF`, **`ENC ≤ 30 e⁻`** (`24,1 e⁻`), `P_false < 10⁻³ / 1 ms`, **`η ≥ 0,99` @ `5 keV`** (`0,99936`), `1 ms` watchdog PASS | Pulser, Lindhard `341,7 e⁻` PHA piki, FPGA logu | RT yasak; `η < 0,99` ise `< 5 cm` kablo / `100 K` temas kontrol edilir |
| **`G4`** | **`S5.5` `1530,1 K` + `S5.6` MBE Rota C** (`Faz E`, `Exp130/139`, `R6`) | `808 nm / 1,0 ms / 43,49 J/cm² ± %5` (**`1530,1 K`**, `%99,99` `{311}` temizliği) + `S5.6` `8 nm` `345 °C` MBE + `350 °C` `FG/H₂`: **`f_act ≥ %85`** (`%99,92`), **`σ_anneal ≤ 0,50 nm`** (`0,430 nm`), kayıp `< %1` (`%0,079`), **`S_ε ≤ 0,40 µeV/√Hz`** (`0,390 µeV/√Hz`) | `10 µs` pirometre, SIMS / `4 K` Hall, RHEED/AFM, SET yük-gürültüsü PSD | Eski `v4.0` `1440 K` (`+1,318 nm` TED!) ve fırın/RTA yasak; `S_ε > 0,50` ise pasivasyon yenilenir |
| **`G5`** | Mıknatıs, Kriyo & `S6.11` TWPA/Purcell (`Faz F`, `Exp125/140`) | `MXC ≤ 25 mK`, `1,500000 T ± 100 ppm` (`17,8 ppm`), **`\|B_res\| ≤ 0,40 T`** (`22,3 µT`), quench `≤ 100 K` (`64,6 K`), `Purcell ≥ 100×` (`625×`), **`F_RO(2 µs) ≥ %99,0`** (`%99,61`) | Termometri, NMR/Hall, VNA `S21`, FAT quench, `ZU48DR` histogram | `\|B_res\| > 0,40 T` ise kalkan ayarlanır; `F_RO < %99` ise TWPA/Purcell ayarlanır |
| **`G6a`** | `Q16.16` BOED-FPGA (`Faz G`, `Exp132/140/145`) | `ZU48DR` `Q16.16` adım **`< 25 µs`** (`2,336 µs`), FP64 paritesi **`abs(ΔRMS) < 1,0 Hz`** (`0,0502 Hz`), canlı `ibm_marrakesh` Ramsey frekans farkı **`< 500 Hz`** (`1,6 Hz`), yuva `≤ 80 ms` (`41,03 ms`), `RMS ≤ 150 Hz` (`72,67 Hz`), `≥ 1` (`≥ 3`) yazmaç | `fpga_boed_dsp.py` + `BayesianSpectroscopy` + `AtlasSelector` | `RMS > 200 Hz` ise durdurma eşiği sıkılaştırılır veya klasik `1 s` taramaya düşülür |
| **`G6b`** | **Risk `R1` `ENDOR` & `f* = %1,5 + 2 MV/m`** (`Faz G`, `Exp129/136/144`) | `≥ 64` donorda **`p_work(f*=%1,5 + 2 MV/m) ≥ %50`** (`Exp136`: `%77,50` / DDRF `%54,00` → `M4 %99,88`; `Exp144` `N=8` `%99,64` blok) ve **`p_work(f=%1,0) ≥ %30`** (`%52,75`) | `≥ 64`-yuva deneysel `ENDOR` + Stark istatistiği & `Exp136/144` kalibrasyonu | `< %35` (`f*=%1,5`) veya `< %15` (`f=%1`) çıkarsa `M2/M4` dondurulur; `f* = %2,0` veya `K=4` revizyonu zorunludur |
| **`G7`** | `XY8`-GRAPE, **`CellISA v4.0`** & **`auto_recal`** (`Faz G`, `Exp126/143/145`) | RF `10–15 kHz`, zorunlu **`XY8` `N = 32–64`** (`N=128`/CPMG yasak), `Q_32D ≥ 0,85`, `D0 ≤ 10⁻⁶`, `CellISA v4.0` (`20` op, canlı `ibm_marrakesh` ön-onaylı) + `auto_recal` (`4/4`) + **`252/252` `pytest`** | 32B tomografi + `ProgramCertificate` JSONL + `auto_recal` arıza testi | `Q < 0,85` ise `N = 32` optimumuna dönülür, `10–15 kHz` RF payı sıkılaştırılır |
| **`G8`** | Maliyet, **`9-RFQ`** & `v6` Modüler Kapı (`Exp128 v6.0` + `Exp144/146`) | `M1 Base` faturaları (`~$2,466M` ref.) + **`9-RFQ`** (`%77,7` nom / `%92,6` MC var) teklifleriyle `M3 Base` `P(Prog>$100M) < %5` (`%4,37`) ve `M3 Full` `P(Prog>$100M) < %5` (`%4,92`; FOAK `%6,90`); `W2/W3` `30 nm` SOI tedarik onayı (`$0,0085/L_fab` `qLDPC`) | `9-RFQ` uzlaştırması + `run_exp128.py` + `run_exp146.py` + `BUTCE_DURUMU.md` | `> $50M` ise gerekçe `BUTCE_DURUMU.md`'ye işlenir; `> $100M` ise `Option-Q/HPC` ertelenerek `M3 Base` (`$5,25M`) veya `256`-hücre pilot (`$4,79M`) seçilir |
