# `M1` Fiziksel Laboratuvar Prototipi Tasarım ve Kurulum Planı (`M1_PROTOTYPE_BLUEPRINT`)

**Sürüm:** `v7.2` (`TRL 1–2 / M0` Kavramsal Prototip Planı — `Exp124–151`, nominal statik `CAD v6.0`, `rtl/boed_fpga/` gerçek açık-kaynak EDA doğrulamalı Verilog RTL [`1.193` LOC], gerçek `%1 ²⁹Si` banyo BOED, `CellISA v4.0` + fiziksel `auto_recal.py` + `ibm_marrakesh` bulut QPU kontrol proxy, `S5.5` `1530,1 K` + `S5.6` LT-MBE Rota C, `S6.11/S6.5` Cryo-MUX/TWPA, **`Exp150` sertifikasız `M0` ön emniyet kiti `S7.SAFETY` (`M1+Safety = $2.611.120`, `iec61508_certified=false`)**, parametrik `BOM_DETAILED v7.0` + `10-RFQ` taslağı, `35/35` staged Atom Litografi `333/333 PASS` [`400/400` yerel] yazılım regresyon testi — 2026-11-25).  
**Dayanak:** [DESIGN.md](DESIGN.md), [MODULAR.md](MODULAR.md), [BOM_DETAILED.csv](BOM_DETAILED.csv) (`v7.0`, `180` parça), [BOM_ENGINEERING.md](BOM_ENGINEERING.md), [RFQ_SPECIFICATIONS.md](RFQ_SPECIFICATIONS.md) (`10-RFQ`), [LITERATURE.md](LITERATURE.md), [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md), `rtl/boed_fpga/README.md`, `research/atom_lithography_machine/cad/cad_verification.json` (`CAD v6.0`: `199` parça nominal statik, `1.108,14 kg` şasi + `355,0 kg` tesis emniyeti), `results/boed_real_bath_benchmark.json`, `results/exp124..151*`.

> **Epistemik Sınır ve Amaç (`TRL 1–2 / M0`):** Bu belge, `M0` kavramsal tasarım, açık-kaynak RTL EDA ve indirgenmiş-mertebe sayısal modelleme (`35/35` staged `333/333` / `400/400` yerel yazılım regresyon testi) aşamasından gelecekteki ilk fiziksel laboratuvar gösterimine (**`M1 Base` / `M1 + Safety`**) geçişin kavramsal planıdır:
> - **Silikon `³¹P/¹²¹Sb/¹⁶⁷Er` fabrikasyon, `Exp150` sertifikasız ön emniyet tasarımı (`iec61508_certified=false`, `semi_s2_certified=false`) & `M1–M4` donanım kurulumu:** `TRL 1–2 (M0)` aşamasındadır (**`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`**). `SEMI`, `SEMI S2` için sertifika vermez; `IEC 61508 SIL-3` bağımsız değerlendirme gerektirir. **`rtl/boed_fpga/` Verilog RTL:** `no_external_eda_sim=false`, `real_eda_verified=true` (`verilator 5.055`, `iverilog 14.0`, `yosys 0.71+101` ön-P&R PASS; **`no_vendor_vivado_pnr=true`, `no_lab_measurement_rtl=true`**).
> - **Kontrol yazılımı (`CellISA v4.0 → OpenQASM 3.0`), `Echo/XY4` DD, `d=3` sendrom dekoderi ve bit-kesin `Q16.16` BOED:** `156`-kübitlik süperiletken `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, `16 PUB × 4.096 shot`, `32,54 s`) üzerinde **bulut süperiletken-QPU kontrol/dekoder proxy kıyaslaması** olarak çalıştırılmıştır (**silikon fabrikasyonunu doğrulamaz**, `0` sızıntı).

---

## 1. `M1 Base` / `M1 + Safety` (`v7.2`) Kavramsal Görev Tanımı, Bütçe Koruması ve Fazlı Yükseltme Yolu
- **Tek Cümlelik Hedef:** Seyreltik epitaksiyel `²⁹Si` banyosu (`f = %1,0` baz ve **`f* = %1,5 + 2 MV/m`** Stark-destekli hedef, Mod B) taşıyan `²⁸Si` test kuponları üzerinde, **`SEMI S2` kılavuzları ve `IEC 61508 SIL-3` mimari hedeflerini referans alan ön emniyet tasarımıyla (`S7.SAFETY-01..06`, `Exp150` — sertifikasız `M0`, saha değerlendirmesi lab fazında)** tek-demet `10→5 keV` sayılmış `³¹P⁺` implantasyonu + `100 K` soğuk-ada IBIC + `S5.5` `1530,1 K` (`43,49 J/cm²`, `OD=8 + 3 mm` çelik kılıf) + `S5.6` `8 nm` LT-MBE Rota C + `S6.9` `PT420` + `MXC` (`~20 mK`, `1,500000 T`) `Q16.16` BOED-FPGA (`rtl/boed_fpga/`, `584` çevrim) + `CellISA v4.0` + `auto_recal.py` ile:
  1. **En az bir (hedef: `≥ 3`) sertifikalı `K=8` (veya `K=4`) çekirdek-spin yazmacını fiziksel olarak doğrulamak ve `CellISA v4.0` + `auto_recal.py` üzerinden `Bell/GHZ-4/BitFlip-3/QFT-3` ve `MUX_READOUT` doğrulamasını koşturmak** `[DESIGN.md §10 | M1]`,
  2. **`G6b` (`Exp129/136` Risk `R1`) `ENDOR` ölçümüyle `f* = %1,5 + 2 MV/m` çalışma verimini (`Exp136`: `%77,50`; `Exp144` `%99,64`; `Exp147` `576`-hücre `%99,27 [N=8] / %99,82 [N=9]`) ve `S5.6` Rota C yük-gürültüsü düşüşünü (`S_ε ≤ 0,40 µeV/√Hz`) laboratuvarda ölçmek.**
- **Finansal ve Stratejik Mantık (`Exp128 v7.0` + `BOM_ENGINEERING.md`, `no_supplier_quotes = true`):**
  - **`M1 Base` nominal donanım tahmini DEĞİŞTİRİLMEDEN KORUNMUŞTUR:** **`$2.466.120`** (`$1.454.996–$4.400.788`).
  - **`M1 + Safety` (`+S7.SAFETY-01..06` sertifikasız `M0` ön emniyet kiti, `+$145.000 / +355,0 kg` harici tesis):** **`$2.611.120`** (`$1.546.996–$4.620.788`, `25` ön FMEA `max RPN 280 → 42 ≤ 60` hedefi).
  - **Fazlı `v7.0` Yükseltme Yolu (`0` Çift Sayım, `$0,00` Köprü):**
    - `M1 Base` / **`M1 + Safety`**: `$2.466.120` / **`$2.611.120`** (`+355,0 kg` tesis)
    - `M3 v5.0 Base` (`167p`, `1.034,94 kg`, `P(Prog>$100M) = %4,44`): `$5.247.800`
    - **Faz-1 Önerilen `M3 Base + Safety` (`173p`, `1.034,94 kg` şasi + `355,0 kg` tesis, `P(Prog>$100M) = %4,67 < %5`, `6/6 CU PASS`):** **`$5.392.800`**
    - `M3 v6.0 Full` (`174p`, `+Option-Q +Option-HPC`, `%4,95`): `$5.547.800`
    - **Faz-2 Hedefi `M3 v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)` (`180p`, `1.108,14 kg` şasi + `355,0 kg` tesis = `1.463,14 kg`, dürüst `%5,22 > %5` [FOAK `%7,25`] → `RFQ-05` kilidi sonrası):** **`$5.692.800`**
  - **Yüksek Yatırım Koruması:** `M1 + Safety` donanımının tamamı (`S7.SAFETY` %100 + çekirdek `M1` `~%84`) doğrudan **Faz-1 `M3 Base + Safety`** ve **Faz-2 `M3 v7.0 Full`** kurulumuna taşınır!

---

## 2. `M3 v7.0 Full` → `M1 Base` / `M1 + Safety` Alt-Sistem İndirgeme Tablosu (`Exp128 v7.0`, `Exp150` & `CAD v6.0` Kilitli)

| Alt Sistem | `M3 v7.0 Full` (`$5.692.800` Nom) | `M1 Base` (`$2.466.120`) / **`M1 + Safety` (`$2.611.120`)** | `M1` Payı | Kilitli Fizik / Mühendislik Şartnamesi (`Exp124–151` & `CAD v6.0`) |
|---|---|---|---:|---|
| **`S1` Kaynak, Kolon & `S1.7` Multi** | Çift hat (`³¹P⁺/²⁹Si⁺`) + `Option-Q` `S1.7-01` `S1-Multi` (`+$68k, 4,8 kg`), `23` parça, **`$484.000`** *(Base `$416k`)* | **Tek hat (`³¹P⁺`, Mod B)** duoplazmatron + `PH₃` kabini + Wien + `HDA-HiRes` + `10→5 keV` kolon (**`$319.750`**; `S1-Multi` sonradan CF40 porttan takılır) | `%66,1` *(`%76,9` Base)* | Kolon `562,66 mm / Ø110 mm / 25,92 kg` (`CAD v6 S1: 30,78 kg`); Wien `0,45 T, R_m=120,6`; **`HDA-HiRes`** (`0,453 eV`); wafer `0 V`, üst gömlek `−5 kV`, anot `+5 kV` (`Exp124/142`) |
| **`S2` Yazma Kafası** | **`32×32 = 1.024` eş-adımlı `0,50 mm`** MEMS/`Arch-B`, `18` parça, `$775.500` | **Tek-delikli mikro-apertür + tek kanal blanker + tek eksenli `Arch-B` lens** (**`$147.750`**) | `%19,1` | **`Arch-B`**: `WD = 0,250 mm`, `E_gap = 10,60 MV/m`, `C_c = 2,660 mm`, `σ_spot = 1,428–1,532 nm`; `v5/v6` birleşik **`σ_tot = 3,588 nm (10 ms) / 3,631 nm (15 ms)`** (`Exp124/139/141`) |
| **`S3` Soğuk-Ada IBIC** | `16×8` kanal vakum-içi CSA + çok-karolu FPGA, `14` parça, `$224.000` | **`1–2` adet 8-kanallı `100 K` soğuk-ada IBIC kartı (`src/board/`) + 1 adet FPGA kartı (`blanker_gate.v`)** (**`$88.550`**) | `%39,5` | **`Exp127` KİLİDİ:** `100 K` `LTC6268` CSA (`Cf=0,25 pF, Rf=1 GΩ`) + `ADA4817-1` (`1,2 µs, ×50`) + `DAC8568` + `TLV3501` (`204` parça, `0` ERC): **`ENC = 24,1 e⁻`**, **`η(5 keV, 0,5 pF) = 0,99936`**, `C_det ≤ 1,5 pF` |
| **`S4` Konum & İnterf.** | Granit + `VC-E` (`VC-G` ops.) + `6-DOF` piezo + 3-eksen interferometre (`Zerodur/Invar-36`), `17` parça, `$253.000` | Aynı yalıtım & `6-DOF` UHV piezo + 2/3-eksen `pm` interferometre + `Zerodur/Invar-36` kaide (**`$233.920`**) | `%92,5` | **`Exp133` kilitli:** `43,57 Hz` PID + `25 dB` FF → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**, **`σ_thermal = 0,0283 nm`** (`20 mK`) |
| **`S5` UHV, `S5.5` `1530,1 K` & `S5.6` MBE** | `s=0,5` UHV (`34,86 L`) + `S5.5` `1530,1 K` (`$95k`) + `S5.6` LT-MBE (`$95k`, `22,4 kg`) + `25`-yonga epi, `24` parça, **`$433.000`** | Aynı UHV + `S5.5` `1530,1 K` (`$66,5k`) + **`S5.6` tam yerinde `8 nm` LT-MBE + `FG/H₂` (`+$95k`)** + `f=%1,0` & `f*=%1,5` lotu (**`$358.300`**) | `%82,7` | **`Exp130/139` (`R6` kapalı):** `v4` `1440 K` (`+1,318 nm` gizli TED!) yasaklandı → **`S5.5` `1530,1 K` (`43,49 J/cm²`, `$0` HW, `%99,99` `{311}` temizliği, `σ_anneal = 0,430 nm`)** + **`S5.6` `345 °C` MBE + `350 °C` `FG/H₂` Rota C (`S_ε = 0,390 µeV/√Hz`, `p_ff = %97,70`)** |
| **`S6` Kriyo, `S6.9`, Mıknatıs, `M4` & `S6.11` MUX** | `20 mK` DR + `PT420` + `S6.9` + `1,5 T` mıknatıs + `56` zincir + `S6.10` (`$171k` net) + `S6.11` `32`-hat TWPA/ZU48DR (`$629,2k`), `42` parça, **`$2.794.100`** | **Aynı `20 mK` DR (`$720k`) + `PT420` + `S6.9` (`$68k`, ZORUNLU) + `1,50 T` mıknatıs (`$185k`) + `2` RF zinciri + `S6.11` `1× ZU48DR` + `1` test TWPA/Purcell/HEMT zinciri (`+$46,85k`)** (**`$1.171.150`**) | `%41,9` | `1,500000 T ± 17,8 ppm`, `22,3 µT`, `64,6 K` (`Exp125`); `Q16.16` `2,336 µs/adım`, `N_mux* = 32` (`F_RO = %99,61`, `625×` Purcell, `Exp140`); **`D3` GRAPE (`p_2q = %0,337–0,395`) + `[[144,12,12]]` `qLDPC` aynı DR'de `120L` taşır (`Exp143/144`)** |
| **`S7–S8` Kontrol, `rtl/boed_fpga/` & `S7.SAFETY`** | `2×` GPU + AWG + SKY130 + **`S7.SAFETY-01..06` (`+$145k, 355 kg` tesis)**, `20+9` parça, **`$349.200`** *(Base `$204,2k`)* | `1×` GPU + `1×` AWG + `1×` EMI + **`machine_control` v4.0 + `rtl/boed_fpga/`** (`$104.450` Base / **`$249.450` `M1+Safety`**) | `%51,1` *(`%71,4` `M1+S`)* | **`rtl/boed_fpga/` (`Exp149`, gerçek EDA):** `1.193` LOC `0 LSB`, `584` çevrim (`verilator`/`iverilog`/`yosys` PASS, `no_vendor_vivado_pnr=true`); **`S7.SAFETY` (`Exp150`, `iec61508_certified=false`):** `25` FMEA `RPN 280→42`; **Canlı `156Q` `ibm_marrakesh` proxy:** XY4 `0,9280`, Bell `0,9733`, `d=3` `5,16×/7,83×`, `Q16.16` `1,6 Hz`; **`35/35` staged `333/333` (`400/400` yerel) `pytest`** |
| **`S9` Sarf, Yedek & `v6` Opsiyonlar** | Yedekler (`$148k`) + `Option-Q` `S9.4` (`+$100k, 4,4 kg`) + `Option-HPC` `S9.HPC` (`+$132k, 64,0 kg`), `13` parça, `$380.000` | Kalibrasyon kuponları + `PH₃` sarfı + tek-eksen yedekleri (**`$42.250`**; `Option-Q/HPC` Faz-2'de tak-çıkar eklenir) | `%11,1` *(`%28,5` Base)* | `Option-Q`: `8.403×–25.122×` `qRAM` ömür (`+0,78 µW @ 20 mK`); `Option-HPC`: `qLDPC 108L 2,32 µs < 2,62 µs` (`2.195 W`, `0 W` kriyo) |

---

## 3. `M1 Base` / `M1 + Safety` (`v7.0`) Fiziksel Mimari ve Sinyal Akışı (`Exp124–151` & `CAD v6.0` Kilitli)

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
> 3. **Silikon-Dışı Kontrol Vekili Kıyaslaması (`Exp145`):** `M8` yazılım kontrol yığını (`CellISA v4.0`, `Q16.16` BOED, `Echo/XY4` DD, `d=3` MWPM), süperiletken `156Q` `ibm_marrakesh` bulut QPU üzerinde silikon-dışı yazılım/kontrol vekili (`proxy`) olarak koşturulmuştur; bu kıyaslama yalnızca yazılım/kontrol derleyici akışını sınar, silikon `³¹P` atom donanımının fiziksel doğrulaması değildir ve laboratuvar devreye alma kapılarını (`G1`–`G8`) ikame etmez.

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
1. **`Q16.16` BOED-FPGA (`Exp132/140/145`):** `ZU48DR` (`fpga_boed_dsp.py`) üzerinde adım gecikmesi `< 25 µs` (**`2,336 µs`**), FP64 paritesi `abs(ΔRMS) < 1,0 Hz` (**`0,0502 Hz`**; ayrı `ibm_marrakesh` silikon-dışı kontrol vekili Ramsey `Δf` paritesi **`1,6 Hz < 500 Hz`**), ortalama yuva `≤ 80 ms` (`41,03 ms`), `RMS ≤ 150 Hz` (`72,67 Hz`), `FNR ≤ %1`, `FPR ≤ %0,5`.
2. **`G6b` — Risk `R1` `ENDOR` & `E_z = 2 MV/m` Stark Verim Kapısı (`Exp129/136/144`):** `≥ 64` donorda **`p_work(f*=%1,5 + 2 MV/m) ≥ %50`** (`Exp136`: `%77,50` / DDRF `%54,00` → `M4 %99,88`; `Exp144` `N_cand = 8` **`%99,64` `qLDPC` blok verimi**) ve **`p_work(f=%1,0) ≥ %30`** (`%52,75`) kanıtlanır. Altında kalınırsa `f* = %2,0` (`XY8 T₂e = 10,8 ms`) veya `K=4` revizyonu uygulanır.
3. **`XY8`-GRAPE, `CellISA v4.0` & `auto_recal.py` (`Exp126/143/145`):** RF payı `10–15 kHz`, zorunlu **`XY8` `N_total = 32–64`** (`N=32` optimum, `N=128` ve `CPMG` yasak), **`CellISA v4.0`** (`20` komut: `+ QRAM_SWAP, QLDPC_ROUND, AUTO_RECAL`) ile `Bell/GHZ-4/Grover-2/BitFlip-3/QFT-3` koşturulup `Q_32D ≥ 0,85`, `D0(17,5 s) ≤ 10⁻⁶` ve `auto_recal` 4-arıza kurtarma testi doğrulanarak ilk fiziksel SHA-256 `ProgramCertificate` mühürlenir.

---

## 5. Ön EHS Tasarım Hedefi — `SEMI S2` ve `IEC 61508 SIL-3` Referanslı Paket (`Exp150` `S7.SAFETY-01..06`, Sertifikasız `M0`)

> **Sertifikasyon Sınırı:** Bu bölümdeki `S7.SAFETY-01..06` paketi sertifikasız `M0` ön tasarım hedefidir. **SEMI kendi `SEMI S2` kılavuzu için sertifika vermez; `IEC 61508 SIL-3` ise tam emniyet yaşam döngüsü ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir.**

`Exp150` (`7/7 PASS`, `12/12` test, `25` satırlı ön FMEA + `10` düğümlü HAZOP), **`S7.SAFETY-01..06` (`$145.000`, `355,0 kg` harici temizoda tesis yükü, `1.090 W`, `0,0 W` kriyo)** ile modelde maksimum risk puanını **`RPN 280 → 42 ≤ 60` (`-%86,3` ortalama, `0` artık `>60`)** tasarım hedefine indirir:

### 5.1 `PH₃` (Fosfin) Toksik ve Piroforik Gaz Güvenliği Hedefi (`S7.SAFETY-01`)
Fosfin (`PH₃`) renksiz, solunumla hızla ölümcül ve saf hâlde piroforiktir (**`ACGIH TLV-TWA = 0,05 ppm`**, `OSHA PEL = 0,30 ppm`, `NIOSH IDLH = 50 ppm`) `{Literatür}`:
1. **Atmosfer-Altı `SDS` Kaynağı:** Basınçlı `40 bar` silindir (`1.207 ppm` IDLH senaryosu) **yasaktır**; sub-atm adsorban **`SDS` (`< 650 Torr`, `≤ 10 g`)** hedeflenir (`0` advektif kaçak).
2. **Muhafaza & Arıtım:** `SEMI S2/S8` referanslı çift-cidarlı vakum borulamalı kabin + `≥ 250 CFM` kuru kimyasal scrubber (`≥ %99,9`).
3. **Çift-Kademeli `SIL-3` Hedef Kesme:** L1 **`0,02 ppm`** uyarı, L2 **`0,05 ppm`** `≤ 15 s` (`12,0 s`) otomatik kapatma hedefi → model operatör maruziyeti **`0,00715 ppm << 0,05 ppm` TLV (`7×` marj, `6.990×` IDLH marjı)**.

### 5.2 Sınıf-4 `S5.5` Lazer + `22 keV` X-Işını, `SIL-3` Hedef Crowbar, `15 kVA` UPS, He ODH & `80 ms` UHV Vana (`S7.SAFETY-02..06`)
- **`S5.5` Lazer + Bremsstrahlung X-Işını (`S7.SAFETY-02`):** Çıplak `8 mm` safir pencere `22 keV`'de **`10,11 µSv/h`** (`10×` halk limiti üstü) sızdırdığından **`OD = 8` (`808 nm`) + `3 mm` çelik** çift-amaçlı kapalı kılıf hedeflenir (**`1,19×10⁻²³ µSv/h << 0,01 µSv/h`**, gömülü Sınıf-1 hedefi, **`3,2 ms`** `1oo2D` SIL-3 hedef perde, `PFD = 2,34×10⁻⁵`, `10 µs` pirometre kesmesi).
- **`1oo2D` `SIL-3` Hedef PLC & `2 MΩ` Aktif HV Crowbar (`S7.SAFETY-03`):** `E(10/22 kV) = 0,075 / 0,363 J < 0,50 J`, `22 kV → < 50 V` boşalım **`18,26 ms < 50 ms`**.
- **Kriyo He ODH, `ASME DN50` & Quench (`S7.SAFETY-05`):** Kuru `LD400+PT420` (`60 m³` oda **`O₂ = %20,57 >> %19,5`**), `ASME VIII DN50 0,5 barg` tahliye (`16,37× He / 25,72× N₂` marj), `1,563 Ω` quench direnci **`38,15 °C < 55 °C`** (`T_hotspot = 64,62 K`, `5 Gauss < 0,62 m`).
- **`15 kVA` Online LFP UPS & `80 ms` UHV Vana (`S7.SAFETY-04/06`):** `0,0 ms` geçiş, tam yük **`40,0 dk`**, Tier-1 **`213,2 dk`**, fail-close **`80,0 ms` UHV vana** (`Si(100)` oksitlenme **`6,0×10⁻⁴ ML << 0,01 ML`**), `ISO 10156` yanıcı-olmayan **`%5 H₂ / %95 N₂`** akış sınırlayıcı.

---

## 6. `M1 Base` / `M1 + Safety` (`v7.2`) Go/No-Go Çıkış Kapıları (`G1`–`G8`, `G6b` & Ön Emniyet Dahil)

> Aşağıdaki kapıların tamamı laboratuvarda fiziksel olarak geçilmeden `M2` ve Faz-1 `M3 Base + Safety` (`$5,393M`) / Faz-2 `M3 v7.0 Full` (`$5,693M`) yatırımına geçilmez.

| Kapı | Alt Sistem / Faz | Kabul Eşiği (`v7.2` Go Kriteri) | Doğrulama Yöntemi | No-Go / Düzeltme Kuralı |
|---|---|---|---|---|
| **`G1`** | **Ön Emniyet (`S7.SAFETY`, `SEMI S2`/`SIL-3` hedefi)**, UHV & `S6.9` `PT420` (`Faz A–B`, `Exp133/150`, `CAD v6.0`) | `Exp150` `S7.SAFETY` tasarım hedefleri (`25` ön FMEA `max RPN ≤ 60` [`42`], `OD8+3 mm` `< 0,01 µSv/h`, `3,2 ms` perde, `SDS PH₃ < 0,05 ppm`, `2 MΩ` crowbar `< 50 ms`, `15 kVA` UPS `≥ 30/180 dk`, `80 ms` UHV); UHV `≤ 10⁻⁸ mbar`; `CFG4` `σ_stage ≤ 0,25 nm` | Bağımsız üçüncü-taraf `SEMI S2` & `IEC 61508` fonksiyonel emniyet değerlendirmesi, X-ışını/OD/RGA, `15 kVA` yük testi, interferometre PSD | **Bağımsız emniyet değerlendirmesi tamamlanmadan gaz/lazer/HV açılamaz**; `σ_stage > 0,25 nm` ise körük/FF sıkılaştırılır |
| **`G2`** | İyon Kolonu (`Faz B–C`, `Exp124`) | Wien `R_m ≥ 60` (`120,6`); `HDA-HiRes` **`ΔE_FWHM ≤ 0,50 eV`** (`0,453 eV`); `Arch-B` `WD = 0,250 mm`, `E_gap ≤ 12 MV/m`, **`σ_spot ≤ 1,50 nm` @ `5 keV`** (`1,428 nm`) | Wien taraması, RFA, Faraday `B_r`, bıçak-kenarı profili | `σ_spot > 1,6 nm` ise `HDA` yarık daraltılır veya `LMIS` değerlendirilir |
| **`G3`** | Soğuk-Ada IBIC (`Faz D`, `Exp127`) | `100 K` `LTC6268` CSA (`1,2 µs / 1 GΩ`): `C_det ≤ 1,5 pF`, **`ENC ≤ 30 e⁻`** (`24,1 e⁻`), `P_false < 10⁻³ / 1 ms`, **`η ≥ 0,99` @ `5 keV`** (`0,99936`), `1 ms` watchdog PASS | Pulser, Lindhard `341,7 e⁻` PHA piki, FPGA logu | RT yasak; `η < 0,99` ise `< 5 cm` kablo / `100 K` temas kontrol edilir |
| **`G4`** | **`S5.5` `1530,1 K` + `S5.6` MBE Rota C** (`Faz E`, `Exp130/139`, `R6`) | `808 nm / 1,0 ms / 43,49 J/cm² ± %5` (**`1530,1 K`**, `%99,99` `{311}` temizliği) + `S5.6` `8 nm` `345 °C` MBE + `350 °C` `FG/H₂`: **`f_act ≥ %85`** (`%99,92`), **`σ_anneal ≤ 0,50 nm`** (`0,430 nm`), kayıp `< %1` (`%0,079`), **`S_ε ≤ 0,40 µeV/√Hz`** (`0,390 µeV/√Hz`) | `10 µs` pirometre, SIMS / `4 K` Hall, RHEED/AFM, SET yük-gürültüsü PSD | Eski `v4.0` `1440 K` (`+1,318 nm` TED!) ve fırın/RTA yasak; `S_ε > 0,50` ise pasivasyon yenilenir |
| **`G5`** | Mıknatıs, Kriyo & `S6.11` TWPA/Purcell (`Faz F`, `Exp125/140`) | `MXC ≤ 25 mK`, `1,500000 T ± 100 ppm` (`17,8 ppm`), **`\|B_res\| ≤ 0,40 T`** (`22,3 µT`), quench `≤ 100 K` (`64,6 K`), `Purcell ≥ 100×` (`625×`), **`F_RO(2 µs) ≥ %99,0`** (`%99,61`; evrensel `d=18` hedefi `p_meas ≤ %0,15`) | Termometri, NMR/Hall, VNA `S21`, FAT quench, `ZU48DR` histogram | `\|B_res\| > 0,40 T` ise kalkan ayarlanır; `F_RO < %99` ise TWPA/Purcell ayarlanır |
| **`G6a`** | `Q16.16` BOED-FPGA & **`rtl/boed_fpga/`** (`Faz G`, `Exp132/140/145/149`) | `ZU48DR` `rtl/boed_fpga/` `Q16.16` adım **`< 25 µs`** (`584` çevrim = `2,336 µs @ 250 MHz`, `0 LSB`), FP64 paritesi **`abs(ΔRMS) < 1,0 Hz`** (`0,0502 Hz`), `ibm_marrakesh` kontrol vekili Ramsey frekans farkı **`< 500 Hz`** (`1,6 Hz`), yuva `≤ 80 ms` (`41,03 ms`), `RMS ≤ 150 Hz` (`72,67 Hz`) | `rtl/boed_fpga/` Vivado bit-akışı + `fpga_boed_dsp.py` + `AtlasSelector` | `RMS > 200 Hz` ise durdurma eşiği sıkılaştırılır veya klasik `1 s` taramaya düşülür |
| **`G6b`** | **Risk `R1` `ENDOR` & `f* = %1,5 + 2 MV/m`** (`Faz G`, `Exp129/136/144/147`) | `≥ 64` donorda **`p_work(f*=%1,5 + 2 MV/m) ≥ %50`** (`Exp136`: `%77,50` → `M4 %99,88`; `Exp144` `%99,64`; `Exp147` `576`-hücre `%99,27 [N=8] / %99,82 [N=9]`) ve **`p_work(f=%1,0) ≥ %30`** (`%52,75`) | `≥ 64`-yuva deneysel `ENDOR` + Stark istatistiği & `Exp136/144/147` kalibrasyonu | `< %35` (`f*=%1,5`) veya `< %15` (`f=%1`) çıkarsa `M2/M4` dondurulur; `f* = %2,0` veya `K=4` revizyonu zorunludur |
| **`G7`** | `XY8`-GRAPE, **`CellISA v4.0`** & **`auto_recal`** (`Faz G`, `Exp126/143/145/151`) | RF `10–15 kHz`, zorunlu **`XY8` `N = 32–64`** (`N=128`/CPMG yasak), `Q_32D ≥ 0,85`, `D0 ≤ 10⁻⁶`, `CellISA v4.0` (`20` op; `ibm_marrakesh` silikon-dışı kontrol vekili üzerinde denendi — silikon donanımı onaylamaz) + fiziksel `auto_recal` (`4/4`) + **`35/35` staged `333/333` (`400/400` yerel) yazılım regresyon testi** | 32B tomografi + `ProgramCertificate` JSONL + `auto_recal` arıza testi | `Q < 0,85` ise `N = 32` optimumuna dönülür, `10–15 kHz` RF payı sıkılaştırılır |
| **`G8`** | Maliyet, **`10-RFQ`** & Fazlı `v7.0` Kapısı (`Exp128 v7.0` + `Exp151`) | `M1+Safety` (`~$2,611M` ref.) + **`10-RFQ`** (`%78,24` nom / `%92,58` MC var) teklifleriyle **Faz-1 `M3 Base+Safety` (`$5,393M`) `P(Prog>$100M) < %5` (`%4,67`, `6/6 CU PASS`)**; `RFQ-05` fiyat kilidi sonrası Faz-2 `+Option-Q/HPC` (`v7 Full $5,693M`, dürüst `%5,22`) | `10-RFQ` uzlaştırması + `run_exp128.py` + `run_exp151.py` + `BUTCE_DURUMU.md` | `> $50M` ise gerekçe `BUTCE_DURUMU.md`'ye işlenir; `> $100M` riskinde Faz-1 `Base+Safety` kilidi korunur, Faz-2 ertelenir |
