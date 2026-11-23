# Atom Litografi Makinesi — Tedarikçi Teklif İstem (RFQ) Teknik Şartnameleri (`RFQ_SPECIFICATIONS.md` — `v5.0`)

> **Amaç ve Epistemik Kapsam:** `Exp114` ve `Exp128 v5.0` (`100.000` örneklemli Monte Carlo) sonuçları, maliyet belirsizliğinin artık fizik modellerinden değil **`B/C` tedarik duvarından** (`$0,59M–$13,07M` kanonik bant; `BOM_DETAILED v5.0` toplam varyansının **`%92,6`'sı** 8 RFQ paketiyle kapsanır) kaynaklandığını göstermiştir. Bu belge, gerçek tedarikçilerden bağlayıcı fiyat/teslim teklifi toplamak üzere hazırlanmış **8 teknik RFQ paketi (`RFQ-01..RFQ-08`)** içerir. **Aşağıdaki hedef fiyat bantları gerçek teklif değil, `Exp114/128/134/139/140` `{Model-Kalibrasyon-Exp114}` / `{Liste-Çapası}` / `{Varsayım}` referans bütçeleridir (`no_supplier_quotes=true`).**

**Tarih:** 2026-11-23 *(`v5.0` yükseltmesi: **`RFQ-08`** eklendi — `Exp139` `S5.6` In-Situ `²⁸Si` UHV MBE + `Exp140` `S6.5/S6.11` `32`-Kanal Cryo-TWPA/HEMT & `ZU48DR Q16.16` BOED-FPGA; `RFQ-07` çift-sayım kredisiyle netleştirildi)*  
**Kapsam:** `BOM_DETAILED.csv v5.0` (`167` parça, `M3 v5.0 = $5.247.800`) içindeki **`78` kritik parça** — nominal `M3 v5.0` donanım maliyetinin **`%76,4`'ü (`$4.009.100`)**, Monte Carlo BOM maliyet varyansının **`%92,6`'sı**! *(Klasik `RFQ-01..06`: `58` parça, `$2.950.900` [`%56,2`]; `RFQ-01..07`: `70` parça, `$3.284.900` [`%62,6`].)*

| RFQ Kodu | Alt Sistem & BOM Kimlikleri | Paket Kapsamı | `M3 v5.0` Referans Bant (`P10 / P50 / P90`) | `M3 v5.0` Nom Payı | MC Varyans Etkisi |
|---|---|---|---:|---:|---|
| **RFQ-01** | `S1.1, S1.2, S1.3, S1.5, S1.6` | Duoplazmatron (`³¹P⁺/²⁹Si⁺`), Wien (`0,45 T, 150 mm`), `Arch-B` `10→5 keV` kolon, `HDA-HiRes` (`R₀=40 mm, 0,453 eV`) & `PH₃` kabin/yıkayıcı | `$228k / $398k / $731k` | `%7,6` | `Exp124` kolon + güvenlik kilidi |
| **RFQ-02** | `S2.1, S2.2, S2.3` | MEMS Apertür, Blanker & `Arch-B` Mini-Lens Dizisi (`0,50 mm` eş-adım, `32×32 = 1.024` demetcik, `16×` karo, `WD=0,250 mm, σ=1,428 nm`) | `$330k / $661k / $1.387k` | `%12,6` | **#2 Varyans sürücüsü (`%6,0`)** |
| **RFQ-03** | `S4.3, S4.4` | `6-DOF` UHV Kaba+İnce Piezo Kademe (`σ≤0,5 nm`) & 3-Eksen Lazer İnterferometre (`pm`) | `$101k / $163k / $283k` | `%3,1` | Konum hata bütçesi çekirdeği |
| **RFQ-04** | `S6.3` | `8`-Bobinli `1,50 T` / `0,1785 T` (`Ø150` bore / `36 mm` yarık / `Ø352` OD, `17,8 ppm`) Kriyo-Mıknatıs & `Nb RRR>300` Kalkan (`22,3 µT`) | `$106k / $185k / $340k` | `%3,5` | Risk `R7` (`Exp125`) donanım kapanışı |
| **RFQ-05** | `S6.6` (`S6.6-01..07`) | `56–82` Zincir `4 K` InP HEMT LNA (`≤2,8 mW`), Kriyo İzolatör/Koaksiyel + `9000`-ch `NbTiN` Rezonatör | `$409k / $765k / $1.418k` | `%14,6` | **#1 Varyans sürücüsü (`%70,6` — `B/C` duvarı!)** |
| **RFQ-06** | `S6.8 + S6.1` | Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı (`³He/⁴He` GHS) + `PT420` `4 K` Ön-Soğutucu | `$472k / $779k / $1.338k` | `%14,8` | **#3 Varyans sürücüsü (`%5,3`, en uzun teslim)** |
| **RFQ-07 (`v4.0` Net)** | `S5.5 + S6.9 + S6.10` *(net)* | `S5.5` `808 nm` Flaş-Tavlama (`43,49 J/cm²` `v5` reçetesi) + `S6.9` `PT420` Uzak Valf/Körük/Örgü + `S6.10` `3 kΩ` `NbTiN` Veri Yolu, `4 K` `968`-Kapı Çapraz-Anahtar & DC Dipol DAC *(harici kap & 5 GHz RF `RFQ-08`'e taşındı)* | `$187k / $334k / $621k` | `%6,4` | **#5 Varyans sürücüsü (`%2,7`)** |
| **RFQ-08 (`v5.0`)** | **`S5.6 + S6.11` (`Exp140 S6.5`)** | **`v5.0` Paketi (`41,67 kg`):** `S5.6` In-Situ `²⁸Si` UHV MBE Capper + `350 °C` FG/H Pasivasyon (`22,4 kg`, `$95k`) + `S6.5/S6.11` `32`-Kanal `20 mK` TWPA/Purcell + `4 K` HEMT + `96`-Coax + `ZU48DR Q16.16` BOED-FPGA (`19,27 kg`, `$629,2k`) | **`$523k / $724k / $1.070k`** | **`%13,8`** | **#4 Varyans sürücüsü (`%3,4` — `v5.0` donanımı)** |
| **TOPLAM (`v5.0`)** | **78 Kritik Parça** | **8 Stratejik Tedarik Paketi (`RFQ-01..RFQ-08`)** | **`$2,35M / $4,01M / $7,19M`** | **`%76,4`** | **Toplam BOM MC Varyansının `%92,6`'sı** |

---

## RFQ-01 — İyon Kaynağı, `10→5 keV` Yavaşlatma Kolonu, `HDA-HiRes` Enerji Süzgeci & `PH₃` Gaz Güvenliği (`S1.1, S1.2, S1.3, S1.5, S1.6`)

- **BOM Referansı:** `S1.1-01..05`, `S1.2-01..04`, `S1.3-01..05`, `S1.5-01..03`, `S1.6-01..02` (`19` parça; `$227,5k / $398,0k / $730,5k`).
- **Aday Tedarikçi Sınıfı:** Orsay Physics, Raith, Ionoptika, Specs, Tectra, Hiden/Kimball + CS Clean Solutions, Edwards, Entegris, Matheson (`PH₃`).

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **İyon Türleri & Enerji (`Exp124`)** | `³¹P⁺` (baz) + ops. `²⁹Si⁺`; çıkarım `10–15 keV` → yavaşlatma `5,0–20,0 keV` (wafer `0 V`, üst gömlek `−5 kV`, kaynak `+5 kV`) | `V_extract = 10 keV`, `V_land = 5,000 keV`, kolon `562,66 mm / 25,92 kg` | HV bölücü + retarding analizör |
| **Parlaklık & `HDA-HiRes` (`S1.5`)** | Net `B ≥ 7,22×10⁴ A/m²/sr`; `ΔE_FWHM ≤ 0,50 eV` (`Arch-B C_c = 2,660 mm`) | `HDA-HiRes R₀ = 40 mm, ΔE_FWHM = 0,453 eV` (`h=95, OD=110 mm`) | Çift-apertür Faraday + enerji taraması |
| **Wien (`S1.2`) & Yavaşlatma (`Arch-B`)** | `m/Δm ≥ 60`; `WD = 0,250 mm`, `E_gap ≤ 12 MV/m` (`10,60 MV/m`) | `B = 0,45 T, L = 150 mm`, `σ_spot = 1,428 nm` (`σ_tot = 3,665 nm` `v5`) | Kütle tarama FWHM + knife-edge |
| **HV, Vakum & `PH₃` Güvenliği (`S1.6`)** | `ΔV/V ≤ 10⁻⁴`, CF100 `≤ 10⁻⁹ mbar`, `150 °C` bakeout; SEMI S2 `PH₃` kabin+scrubber `< 50 ppb`, `< 5 s` kesme | `≤ 5×10⁻¹⁰ mbar`, `< 10 ppb` egzoz | RGA, `He ≤ 10⁻¹⁰`, PLC kilit testi |

---

## RFQ-02 — MEMS Çok-Demet Apertür, Elektrostatik Blanker & `Arch-B` Mini-Lens Dizisi (`S2.1, S2.2, S2.3`)

- **BOM Referansı:** `S2.1-01..04`, `S2.2-01..04`, `S2.3-01..04` (`12` parça; `$329,5k / $661,0k / $1.387,0k`).
- **Aday Tedarikçi Sınıfı:** IMS Nanofabrication ekosistemi, Fraunhofer IPMS/ISIT, CEA-Leti, LioniX, VTT, IMT Masken.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Dizi Ölçeği & Eş-Adım (`Arch-B`)** | `32×32 = 1.024` demetcik, **`0,50 mm` eş-adım** (`16,0×16,0 mm`, köşegen `22,63 mm < Ø28,0 mm`), `16×` 64-ch karo | `≥ %98` çalışan demetcik verimi (`M2`: `8×8–16×16`) | SEM CD + otomatik süreklilik taraması |
| **Apertür, Blanker & Mini-Lens** | `30 µm` SOI (`±50 nm` CD, `bow ≤ 2 µm`), `V_blank ≤ 35 V`, kapı `≤ 1 ms`, `f₁ ≥ 1,0 MHz` (`2,59 MHz`), 3-yonga `WD=0,250 mm, σ_spot ≤ 1,50 nm` | `σ_spot = 1,428 nm`, `10 µs` kapı, `3 kV` hi-pot | LDV, beyaz-ışık interferometri, knife-edge |
| **Interposer & Vakum** | `LTCC/AlN` + TSV fan-out (`1.024` ch), UHV `≤ 10⁻⁹ mbar`, `150 °C` bakeout, manyetik-olmayan kaset | Tak-çıkar tekrarlanabilirlik `±2 µm` | RGA + kinematik metroloji |

---

## RFQ-03 — `6-DOF` UHV Piezo Kademe & 3-Eksen Lazer İnterferometri (`S4.3, S4.4`)

- **BOM Referansı:** `S4.3-01..04`, `S4.4-01..04` (`8` parça; `$100,5k / $163,0k / $282,5k`).
- **Aday Tedarikçi Sınıfı:** Physik Instrumente (PI PIMars UHV), SmarAct, Attocube; Renishaw (`XL-80`/`RLE`), Zygo, Attocube IDS.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Artık Titreşim & Kademe (`Exp79/133`)** | `6-DOF`, XY `≥ 200 µm` + kaba `±25 mm`, `σ_kademe ≤ 0,50 nm` RMS (`VC-E` zemin) | `σ_stage = 0,1024 nm` (`Exp133 CFG4`), `0,1 nm` çözünürlük | Kapalı-çevrim interferometre PSD |
| **İnterferometre & Arayüz (`S4.4`)** | 3-eksen diferansiyel (`≤ 0,05 nm`), `μ_r < 1,01`, UHV `≤ 10⁻⁹ mbar`, gecikme `< 5 µs` | `10 pm`, `±0,05 ppm`, `< 1 µs` EtherCAT/SPI | Sabit ayna sürüklenme + osiloskop |

---

## RFQ-04 — `8`-Bobinli `1,50 T` / `0,1785 T` Kriyo-Mıknatıs & `Nb (RRR>300)` Kalkan (`S6.3`, `Exp125/131`)

- **BOM Referansı:** `S6.3-01..05` (`5` parça; `$106,0k / $185,0k / $340,0k`).
- **Aday Tedarikçi Sınıfı:** Cryomagnetics, American Magnetics (AMI), Oxford Instruments NanoScience, Cryogenic Ltd., Janis/Lake Shore.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Bobin & Çift-Kip Alan (`Exp125/131`)** | `8`-bobin (`Ø150` bore / `36 mm` yarık / `Ø352` OD); `0,15–1,50 T` (`1,500 T` ESR + **`0,1785 T` `M4`**), `ΔB/B₀ ≤ 10⁻⁴` | `17,8 ppm`, `I/I_c = 0,212`, `σ_hoop = 52,7 MPa`, `≤ 0,1 ppm/saat` | `4,2 K` NMR / 3-eksen Hall haritası |
| **Kalkan, `4 K` Yük & Quench** | `Nb (RRR>300)` + `Cryoperm-10`: `z=−155 mm`'de `B_res ≤ 0,40 T`; HTS `4 K` yük `≤ 100 mW`; quench `≤ 100 K` | `B_res = 22,3 µT`, `T_quench = 64,6 K`, `4 K ≤ 50 mW` | Hall taraması + FAT quench testi |

---

## RFQ-05 — Fab Okuma Zinciri: `56×` Kriyo-LNA (`≤ 2,8 mW`), İzolatör/Koaksiyel & `9000`-ch `NbTiN` (`S6.6`) — **`B/C` DUVARI KIRICI**

- **BOM Referansı:** `S6.6-01..07` (`7` parça; `$409,0k / $765,4k / $1.418,2k`; BOM MC varyansının **`%70,6`'sı**).
- **Aday Tedarikçi Sınıfı:** Low Noise Factory (LNF), CMT, B&Z (LNA); LNF/Quinstar/QMC (izolatör); Delft Circuits, Bluefors, Keycom (koaksiyel); AMD (`ZCU216`); VTT/QuTech/SeeQC (`NbTiN`).

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Zincir & `4 K` LNA (`Exp111/112/113`)** | `56–82` zincir (`NL=110–160`), `P_DC ≤ 7,8 mW` (`PT420`) / `≤ 2,8 mW` (`PT410`), `T_n ≤ 4,0 K`, `P_1dB ≥ −55 dBm` | `≤ 2,1 mW`, `T_n ≤ 2,0 K`, `≥ 38 dB`, `IP3 ≥ −40 dBm` | `4 K` Y-faktörü + iki-ton IMD3 |
| **İzolatör, Koaksiyel, `NbTiN` & RFSoC** | İzolasyon `≥ 20 dB`, `NbTi` çıkış `< 0,1 dB/m`, `NbTiN` `Q_i ≥ 10⁵ @ ≤0,4 T`, `σ_f ≤ %0,27`, `14× ZCU216` | `≥ 35 dB`, `Q_i ≥ 2×10⁵`, `8` hat/kart (`7` kart) ops. | `20 mK` VNA çentik + SFDR `> 60 dBc` |

---

## RFQ-06 — Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı & `PT420` Ön-Soğutucu (`S6.8 + S6.1`)

- **BOM Referansı:** `S6.8-01..04`, `S6.1-01..03` (`7` parça; `$471,5k / $778,5k / $1.337,5k`).
- **Aday Tedarikçi Sınıfı:** Bluefors (`LD400/XLD`), Oxford Instruments (`Proteox`), Leiden Cryogenics, FormFactor/Janis.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Kriyo Güç & `³He` GHS (`Exp110/121/140`)** | `T_base ≤ 20 mK`, `≥ 250 µW @ 100 mK` (`LD400`: `14 µW @ 20 mK`), `PT420 ≥ 1,5 W @ 4,2 K`, `~20 L STP ³He` | `≤ 12 mK`, `400 µW @ 100 mK`, `2,0 W @ 4,2 K`, `< 36 s` soğuma | Isıtıcı yük eğrisi + 72 saat burn-in |
| **Arayüzler (`RFQ-04/07/08`)** | `≥ 120` fab koaksiyel + **`96` `v5.0` `S6.5` koaksiyel** (`1.024`-hücre `M4` tavanı `2.887` hücre) + `S6.9` körük/örgü + `S5.1` UHV | `10.000`-hücre `M4` için modüler `≥ 4× LD400` veya `XLD1000` ops. | STEP ICD + `He ≤ 10⁻¹⁰ mbar·L/s` |

---

## RFQ-07 (`v4.0` Net) — `S5.5` Flaş-Tavlama Optik Kafası, `S6.9` `PT420` Ayrıştırma & `S6.10` `M4` `3 kΩ` `NbTiN` / `4 K` Çapraz-Anahtar

- **BOM Referansı (`v5.0` Net — Çift-Sayım Temiz):** `S5.5-01..04` (`$95k`), `S6.9-01..04` (`$68k`), `S6.10-01/03/04` (`$171k` net; `S6.10-02` harici kaplama `$54k` → `RFQ-08A S5.6` ve `S6.10-04` 5 GHz RF `$20k` → `RFQ-08B S6.11-01` taşındı) — **`12` satır (`11` fiyatlı), `$187,0k / $334,0k / $621,0k` (`{Varsayım}`)**.

| Alt-Lot & Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **7A (`S5.5`) `808 nm` Flaş & Safir (`Exp130/139`)** | `808 nm` qCW `84×88×84 mm` düz-tepe (`≤ ±%2`), **`v5` küme-temizleyici `43,49 J/cm² / 1,0 ms` (`1530,1 K = 0,907 T_melt`, `F_win=11,16 J/cm²`, `8,96× LIDT`)**, `+Y` CF63 safir (`Ø44 mm CA, T_AR ≥ %97`), `10 µs` pirometre, MXC `<1 K` deklanşör (`<5 ms`) | `%99,99` `{311}` çözünmesi, `σ_anneal = 0,430 nm`, `Exp124 σ_tot = 3,665 nm`; Mod 1 (`16×16 mm`) / Mod 2 (`4×4 mm` M1) | Enerji/profil ölçümü + LIDT + PLC kilit |
| **7B (`S6.9`) `PT420` Ayrıştırma (`Exp133`)** | `500 mm` uzak valf + `600 mm` He hattı; kenar-kaynaklı `316L` CF63 körük (`ID=44/OD=68/L=120 mm, k ≤ 6.282 N/m`); `4×` S-ilmek OFHC Cu örgü (`RRR ≥ 200, k ≤ 60 N/m`); `1,4–21 Hz` `25 dB` FF | `k_bellows = 2.000 N/m`, `k_braid = 52,7 N/m` (`ΔT = 3,7 mK`), `σ_stage = 0,1024 nm`, `σ_pointing = 0,1473 nm` (`VC-E`) | Yay sabiti + `20 mK` iletkenlik + PSD |
| **7C (`S6.10` Net) `3 kΩ` `NbTiN` & `4 K` `968`-Kapı (`Exp131`)** | `NbTiN` (`t=9 nm, w=100 nm, L_□=100 pH/□, Z_r=3 kΩ, f_r=5,0 GHz, L_res=300 µm, B_M4=0,1785 T`); `4 K` `SKY130` `968`-kapı çapraz-anahtar (`15,4 mW @ 4 K`); `20-bit` DC dipol bias DAC (`< 0,5 µV/√Hz`) | `F_iSWAP = 0,9655–0,9918`, `L=11 FT` `%99,40` perkolasyon, `±0,2 mV` bias | `20 mK` VNA (`0,1785 T`) + `4 K` tarama |

---

## RFQ-08 (`v5.0`) — `S5.6` In-Situ `²⁸Si` UHV MBE Capper + `S6.5/S6.11` `32`-Kanal Cryo-TWPA/HEMT & `ZU48DR Q16.16` BOED-FPGA

- **BOM Referansı:** `S5.6-01..04` (`22,4 kg`, `$67,0k / $95,0k / $145,0k`) + `S6.11-01..04` (`Exp140 S6.5-01..04`, `19,27 kg` [`7,77 kg` soğuk + `11,50 kg` raf], `$456,4k / $629,2k / $925,2k`) — **`8` parça, `41,67 kg`, referans bant `$523,4k / $724,2k / $1.070,2k` (`%13,8` of `M3 v5.0`, `{Liste-Çapası}/{Varsayım}`)**.
- **Birincil Şartname Kaynakları:** `results/exp139_epi_cap_process_integration/s56_hardware_spec.json` (`H157`) ve `results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json` (`H158`).
- **Aday Tedarikçi Sınıfı (2 Alt-Lot):**
  - **Lot 8A (`S5.6` UHV MBE Capper & FG/H):** Dr. Eberl MBE-Komponenten (`SUSI-63`), CreaTec, Mantis Deposition, Scienta Omicron (`²⁸Si` potasız süblimasyon + `PBN` ısıtıcı); Inficon (`QCM`); SAES Getters + Pfeiffer (`80 L/s TMP + NEG`); Isonics / Air Liquide (`<50 ppm ²⁹Si` çubuk).
  - **Lot 8B (`S6.11` / `Exp140 S6.5` Cryo-MUX + RFSoC):** AMD/Xilinx + HiTech Global / Abaco (`ZU48DR RFSoC`); Silent Waves, ArgoQ, MIT LL / NIST iş ortağı / SeeQC (`20 mK` Josephson TWPA + Purcell); Low Noise Factory (`LNF-LNC4_8C` `32×` `4–8 GHz` HEMT); Delft Circuits / Coax Co. / Bluefors (`96×` `0,86 mm` `CuNi/NbTi` koaksiyel demet).

### Teknik Şartname & FAT Tablosu (`RFQ-08` — `Exp139` & `Exp140` Kilitli Parametreleri)

| Alt-Lot & Parça | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | FAT / SAT Doğrulama Yöntemi |
|---|---|---|---|
| **8A (`S5.6-01/02`) Potasız `²⁸Si` MBE & QCM (`Exp139`)** | `s5_loadlock_chamber` `+Z` `CF100` montaj (`Ø152×280 mm`, `Z=585..865 mm`, min boşluk `≥ 70 mm`); kütle `11,8 + 3,4 = 15,2 kg`; `P_base ≤ 2×10⁻¹⁰`, `P_growth ≤ 5×10⁻¹⁰ Torr`; `0,05–0,20 nm/s`; `²⁸Si` çubuk `< 50 ppm ²⁹Si` (`~5 g`, `>1.000` yonga); kalınlık **`8,0 ± 0,3 nm`** | `P_base = 1,5×10⁻¹⁰`, `P_growth = 3,5×10⁻¹⁰ Torr`, `0,10 nm/s` (`80 s`), `400 W` büyüme / `25 W` bekleme, `0,00 µW` kriyo yük | FAT: QCM + XTEM/ellipsometri (`8,0 ± 0,3 nm`), SIMS `²⁹Si < 50 ppm`, `He ≤ 10⁻¹⁰ mbar·L/s` |
| **8A (`S5.6-03/04`) `345 °C` PBN Isıtıcı, FG/H & TMP/NEG (`Exp139`)** | `PBN` radyatif chuck (`RT–450 °C`, `±2 °C`, `150 W`); `%5 H₂/N₂` FG (veya atomik-H) sızıntı vanası `350 °C / 15 dk`; kompakt `80 L/s TMP + NEG`; kütle `4,2 + 3,0 = 7,2 kg` (`S5.6` toplam **`22,4 kg`**) | `T_epi* = 345 °C` (`R_q = 0,091 nm, h_epi = 236 nm`), Rota C `S_ε = 0,390 µeV/√Hz` (`F_ff = %97,70`), `%0` boru-hattı cezası (`28,3 < 73 dk`) | FAT: `345 °C` 24s termal kararlılık + RGA + tam-metal vana `20 mK` ısı yalıtımı (`0,00 µW`) |
| **8B (`S6.11-01` / `S6.5-01`) `ZU48DR Q16.16` BOED-FPGA (`Exp140`)** | `2× AMD/Xilinx ZU48DR RFSoC` `2U 19"` şase (`482,6×520×88,9 mm`, **`11,50 kg`**, `≤ 100 W @ 300 K`, `0 W` kriyo); `32` Direct-RF zincir; `250 MHz` `Q16.16` BOED-FPGA adım gecikmesi **`≤ 25 µs`**, `FP64` farkı **`≤ 1,0 Hz`** | `2,336 µs/adım` (`584` çevrim, `10,7×` marj), `abs(ΔRMS) = 0,050 Hz`, `ΔFNR = ΔFPR = %0`, `87,96 W`, `%10,5` DSP48E2 | FAT: `400`-adaylı bit-doğru donanım loopback (`Q16.16 vs FP64`) + `10 MHz` saat kilidi + `CellISA v3.5` sendrom testi |
| **8B (`S6.11-02` / `S6.5-02`) `32×` `20 mK` TWPA + Purcell (`Exp140`)** | `32` adet `4–8 GHz` Josephson TWPA + ortak bant-geçiren Purcell filtresi (`κ_p = 80 MHz`) + çift kriyo-izolatör (`180×140×55 mm`, **`2,72 kg`**); `T_N ≤ 0,50 K`, `G ≥ 18 dB`, `P_1dB ≥ −98 dBm`, `20 mK` toplam yük `≤ 4 µW` | `T_N = 0,30 K`, `G = 20 dB`, **`625×` Purcell** (`T_1 = 124,3 ms`), `N_mux* = 32` (`100 MHz` aralık, `F_RO = 0,9961 @ 2 µs`), `2,144 µW @ 20 mK` | FAT: `20 mK` S21/kazanç/gürültü sıcaklığı + 32-ton sıkışma (`P_peak = −98,6 dBm`, `≥ 1 dB` BO) raporu |
| **8B (`S6.11-03` / `S6.5-03`) `32×` `4 K` HEMT Bankası (`Exp140`)** | `32` adet `4–8 GHz` InP HEMT (`LNF-LNC4_8C` sınıfı; `220×120×40 mm`, **`1,02 kg`**); `T_n ≤ 2,5 K`, `P_DC ≤ 7,8 mW/hat` (`≤ 0,25 W @ 4 K`) | `T_n = 2,0 K` (`T_sys = 0,672 K`, `η_meas = %21,43`), `0,2496 W @ 4 K` (`2,1 mW` ops. ile `0,067 W`) | FAT: `32/32` seri-numaralı `4 K` kazanç, `T_n` ve `P_DC` sertifikası |
| **8B (`S6.11-04` / `S6.5-04`) `96`-Hat Kriyo-Koaksiyel (`Exp140`)** | `96` hat (`32` RO giriş + `32` RO çıkış + `32` XY; `0,86 mm` `CuNi/NbTi`, `95×95×620 mm`, **`4,03 kg`**); `S6.5` toplam soğuk kütle **`7,77 kg`** (`19,27 kg` toplam); `LD400/PT420` 4-kademe yükü kapalı | `20 mK = 6,256 / 14 µW`, `100 mK = 59,58 / 400 µW`, `4 K = 0,488 / 2,0 W`, `50 K = 8,26 / 40 W` (`< %50` pay!) | FAT: Oda + `4 K` S21 (`≤ 0,1 dB/m` NbTi) + kademe termal iletkenlik doğrulaması |

### Teklif Soruları (`RFQ-08` — Pilot vs Tam `1.024`-Hücre & `10k` Ölçekleme)
1. *(Lot 8A)* Potasız DC `²⁸Si` süblimasyon kaynağı + `PBN` ısıtıcı + `80 L/s` TMP/NEG tek anahtar-teslim `CF100` modül olarak tedarik edildiğinde teslim süresi ve `5 g` `< 50 ppm ²⁹Si` çubuk opsiyon bedeli nedir?
2. *(Lot 8B)* Kademeli alım fiyatlandırması: **`M1` (`1× ZU48DR + 1` TWPA/HEMT/coax test zinciri, `~$46,9k`)** vs **`M3 v5.0` Pilot (`256`-hücre / `8`-hat + `1× ZU48DR`, `~$171,8k`)** vs **`M3 v5.0` Tam (`1.024`-hücre / `32`-hat + `2× ZU48DR`, `~$629,2k`)** fiyat kırılımları nelerdir?
3. *(Lot 8B — `10.000`-Hücre Notu)* `Exp140` tek `LD400/PT420` tavanını `2.887` hücre olarak kanıtlamıştır; `32×` TWPA modülünün `4×` modüler kriyostata (`10.000` hücre) ölçeklenmesinde çoklu-adet TWPA/HEMT indirim oranları nedir?

---

## Teklif Toplama Sonrası Kapanış Protokolü (`Exp128 v5.0` → Fiziksel Tedarik)

1. Sekiz RFQ'dan (`RFQ-01..RFQ-08`, nominal `%76,4` / MC varyans `%92,6`) gelen bağlayıcı fiyat teklifleri `BOM_DETAILED.csv`'deki `{Model-Kalibrasyon-Exp114}` / `{Varsayım}` hücrelerinin yerine `{Teklif-Çapası}` etiketiyle yazılır (kanonik `BOM.csv` yine değiştirilmez).
2. `experiments/exp128_bom_sensitivity/run_exp128.py` gerçek tekliflerle yeniden koşturulur; özellikle `S6.6` (`RFQ-05`) `B/C` sınıfı ve `S6.11-02` (`RFQ-08B` `32×` TWPA) birim fiyatı kesinleştirilerek `P(Program > $100M)` (`%4,23`) ve FOAK 5y TCO (`%5,91`) kuyruk riski daraltılır.
3. Teklif sonrası `Program` tahmini `$50M` yumuşak çizgisini aşarsa teknik gerekçe kayda geçirilir; `$100M` kesin sınırı tehdit altındaysa **`M3 v5.0` `256`-hücreli Pilot (`$4,79M` HW)** kademeli dağıtım seçeneği tetiklenir.
