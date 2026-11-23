# Atom Litografi Makinesi — Tedarikçi Teklif İstem (RFQ) Teknik Şartnameleri (`RFQ_SPECIFICATIONS.md` — `v6.0`)

> **Amaç ve Epistemik Kapsam:** `Exp114` ve `Exp128 v6.0` (`100.000` örneklemli Monte Carlo) sonuçları, maliyet belirsizliğinin fizik modellerinden değil **`B/C` tedarik duvarından** (`$0,59M–$13,07M` kanonik bant; `BOM_DETAILED v6.0` toplam varyansının **`%92,6`'sı** 9 RFQ paketiyle kapsanır) kaynaklandığını göstermiştir. Bu belge, gerçek tedarikçilerden bağlayıcı fiyat/teslim teklifi toplamak üzere hazırlanmış **9 teknik RFQ paketi (`RFQ-01..RFQ-09`)** içerir. **Aşağıdaki hedef fiyat bantları gerçek teklif değil, `Exp114/128/134/139/140/142/143` `{Model-Kalibrasyon-Exp114}` / `{Liste-Çapası}` / `{Varsayım}` referans bütçeleridir (`no_supplier_quotes=true`).**

**Tarih:** 2026-11-23 *(`v6.0` yükseltmesi: **`RFQ-09`** eklendi — `Exp142` `Option-Q` [`5`-kademe Chebyshev `NbTiN` `qRAM` + `S1-Multi` kartuş + `1550 nm` fiber, `9,20 kg`, `$168k`] & `Exp143` `Option-HPC` [`4U` `100G` RoCEv2 RDMA dekoder `FAT < 6,7 µs` `d=37` / `< 2,6 µs` `qLDPC`, `64,00 kg`, `$132k`])*  
**Kapsam:** `BOM_DETAILED.csv v6.0` (`174` parça, `M3 v6.0 Full = $5.547.800` [`M3 v5.0 Base = $5.247.800`]) içindeki **`85` kritik parça** — nominal `M3 v6.0 Full` donanım maliyetinin **`%77,7`'si (`$4.309.100`)**, Monte Carlo BOM maliyet varyansının **`%92,6`'sı**! *(Klasik `RFQ-01..06`: `58` parça, `$2.950.900` [`%53,2`]; `RFQ-01..08` `v5.0 Base`: `78` parça, `$4.009.100` [`v5 Base`'in `%76,4`'ü, `v6 Full`'ün `%72,3`'ü].)*

| RFQ Kodu | Alt Sistem & BOM Kimlikleri | Paket Kapsamı | `M3 v6.0` Referans Bant (`P10 / P50 / P90`) | `M3 v6` Nom Payı | MC Varyans Etkisi |
|---|---|---|---:|---:|---|
| **RFQ-01** | `S1.1, S1.2, S1.3, S1.5, S1.6` | Duoplazmatron (`³¹P⁺/²⁹Si⁺`), Wien (`0,45 T, 150 mm`), `Arch-B` `10→5 keV` kolon, `HDA-HiRes` (`R₀=40 mm, 0,453 eV`) & `PH₃` kabin/yıkayıcı | `$228k / $398k / $731k` | `%7,2` | `Exp124` kolon + güvenlik kilidi |
| **RFQ-02** | `S2.1, S2.2, S2.3` | MEMS Apertür, Blanker & `Arch-B` Mini-Lens Dizisi (`0,50 mm` eş-adım, `32×32 = 1.024` demetcik, `16×` karo, `WD=0,250 mm, σ=1,428 nm`) | `$330k / $661k / $1.387k` | `%11,9` | **#2 Varyans sürücüsü (`%6,0`)** |
| **RFQ-03** | `S4.3, S4.4` | `6-DOF` UHV Kaba+İnce Piezo Kademe (`σ≤0,5 nm`) & 3-Eksen Lazer İnterferometre (`pm`) | `$101k / $163k / $283k` | `%2,9` | Konum hata bütçesi çekirdeği |
| **RFQ-04** | `S6.3` | `8`-Bobinli `1,50 T` / `0,1785 T` (`Ø150` bore / `36 mm` yarık / `Ø352` OD, `17,8 ppm`) Kriyo-Mıknatıs & `Nb RRR>300` Kalkan (`22,3 µT`) | `$106k / $185k / $340k` | `%3,3` | Risk `R7` (`Exp125`) donanım kapanışı |
| **RFQ-05** | `S6.6` (`S6.6-01..07`) | `56–82` Zincir `4 K` InP HEMT LNA (`≤2,8 mW`), Kriyo İzolatör/Koaksiyel + `9000`-ch `NbTiN` Rezonatör | `$409k / $765k / $1.418k` | `%13,8` | **#1 Varyans sürücüsü (`%70,0` — `B/C` duvarı!)** |
| **RFQ-06** | `S6.8 + S6.1` | Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı (`³He/⁴He` GHS) + `PT420` `4 K` Ön-Soğutucu | `$472k / $779k / $1.338k` | `%14,0` | **#3 Varyans sürücüsü (`%5,3`, en uzun teslim)** |
| **RFQ-07 (`v4.0` Net)** | `S5.5 + S6.9 + S6.10` *(net)* | `S5.5` `808 nm` Flaş-Tavlama (`43,49 J/cm²` `v5` reçetesi) + `S6.9` `PT420` Uzak Valf/Körük/Örgü + `S6.10` `3 kΩ` `NbTiN` Veri Yolu, `4 K` `968`-Kapı Çapraz-Anahtar & DC Dipol DAC | `$187k / $334k / $621k` | `%6,0` | **#5 Varyans sürücüsü (`%2,7`)** |
| **RFQ-08 (`v5.0`)** | `S5.6 + S6.11` (`Exp140 S6.5`) | `S5.6` In-Situ `²⁸Si` UHV MBE Capper + `350 °C` FG/H (`22,40 kg`, `$95k`) + `S6.5/S6.11` `32`-ch TWPA/HEMT + `96`-Coax + `ZU48DR Q16.16` BOED-FPGA (`19,27 kg`, `$629,2k`) | `$523k / $724k / $1.070k` | `%13,1` | **#4 Varyans sürücüsü (`%3,3`)** |
| **RFQ-09 (`v6.0` Modüler)** | **`S1.7 + S9.4 + S9.HPC`** | **`Option-Q` (`9,20 kg`, `$168k`):** `5`-kademe Chebyshev `NbTiN` `qRAM` + `S1-Multi` (`³¹P/¹²¹Sb/¹⁶⁷Er`) + `1550 nm` fiber; **`Option-HPC` (`64,00 kg`, `$132k`):** `4U` `100G` RoCEv2 RDMA QEC dekoder rafı + `QSFP28` köprü | **`$216k / $300k / $423k`** | **`%5,4`** | **Modüler opsiyon (`%0,8` var.: `%0,5` OptQ + `%0,3` OptHPC)** |
| **TOPLAM (`v6.0 Full`)** | **85 Kritik Parça** | **9 Stratejik Tedarik Paketi (`RFQ-01..RFQ-09`)** | **`$2,57M / $4,31M / $7,61M`** | **`%77,7`** | **Toplam BOM MC Varyansının `%92,6`'sı** |

---

## RFQ-01 — İyon Kaynağı, `10→5 keV` Yavaşlatma Kolonu, `HDA-HiRes` Enerji Süzgeci & `PH₃` Gaz Güvenliği (`S1.1, S1.2, S1.3, S1.5, S1.6`)

- **BOM Referansı:** `S1.1-01..05`, `S1.2-01..04`, `S1.3-01..05`, `S1.5-01..03`, `S1.6-01..02` (`19` parça; `$227,5k / $398,0k / $730,5k`).
- **Aday Tedarikçi Sınıfı:** Orsay Physics, Raith, Ionoptika, Specs, Tectra, Hiden/Kimball + CS Clean Solutions, Edwards, Entegris, Matheson (`PH₃`).

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **İyon Türleri & Enerji (`Exp124`)** | `³¹P⁺` (baz) + ops. `²⁹Si⁺`; çıkarım `10–15 keV` → yavaşlatma `5,0–20,0 keV` (wafer `0 V`, üst gömlek `−5 kV`, kaynak `+5 kV`) | `V_extract = 10 keV`, `V_land = 5,000 keV`, kolon `562,66 mm / 25,92 kg` | HV bölücü + retarding analizör |
| **Parlaklık & `HDA-HiRes` (`S1.5`)** | Net `B ≥ 7,22×10⁴ A/m²/sr`; `ΔE_FWHM ≤ 0,50 eV` (`Arch-B C_c = 2,660 mm`) | `HDA-HiRes R₀ = 40 mm, ΔE_FWHM = 0,453 eV` (`h=95, OD=110 mm`) | Çift-apertür Faraday + enerji taraması |
| **Wien (`S1.2`) & Yavaşlatma (`Arch-B`)** | `m/Δm ≥ 60`; `WD = 0,250 mm`, `E_gap ≤ 12 MV/m` (`10,60 MV/m`) | `B = 0,45 T, L = 150 mm`, `σ_spot = 1,428 nm` (`σ_tot = 3,665 nm` `v5/v6`) | Kütle tarama FWHM + knife-edge |
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

- **BOM Referansı:** `S6.6-01..07` (`7` parça; `$409,0k / $765,4k / $1.418,2k`; BOM MC varyansının **`%70,0`'ı**).
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
| **Arayüzler (`RFQ-04/07/08/09`)** | `≥ 120` fab + `96` `v5.0` `S6.5` koaksiyel + **`−X` `CF63` `Option-Q` yan portu** (`4` koaks + `1550 nm` fiber, `0,78 µW @ 20 mK`) + `S6.9` körük | `10.000`-hücre `M4` için modüler `≥ 4× LD400` veya `XLD1000` ops. | STEP ICD + `He ≤ 10⁻¹⁰ mbar·L/s` |

---

## RFQ-07 (`v4.0` Net) — `S5.5` Flaş-Tavlama Optik Kafası, `S6.9` `PT420` Ayrıştırma & `S6.10` `M4` `3 kΩ` `NbTiN` / `4 K` Çapraz-Anahtar

- **BOM Referansı (`v5.0/v6.0` Net — Çift-Sayım Temiz):** `S5.5-01..04` (`$95k`), `S6.9-01..04` (`$68k`), `S6.10-01/03/04` (`$171k` net; `S6.10-02` harici kaplama `$54k` → `RFQ-08A S5.6` ve `S6.10-04` 5 GHz RF `$20k` → `RFQ-08B S6.11-01` taşındı) — **`12` satır (`11` fiyatlı), `$187,0k / $334,0k / $621,0k` (`{Varsayım}`)**.

| Alt-Lot & Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **7A (`S5.5`) `808 nm` Flaş & Safir (`Exp130/139`)** | `808 nm` qCW `84×88×84 mm` düz-tepe (`≤ ±%2`), `v5/v6` küme-temizleyici `43,49 J/cm² / 1,0 ms` (`1530,1 K = 0,907 T_melt`, `F_win=11,16 J/cm²`, `8,96× LIDT`), `+Y` CF63 safir (`Ø44 mm CA`), `10 µs` pirometre, MXC `<1 K` deklanşör | `%99,99` `{311}` çözünmesi, `σ_anneal = 0,430 nm`, `Exp124 σ_tot = 3,665 nm`; Mod 1 (`16×16 mm`) / Mod 2 (`4×4 mm` M1) | Enerji/profil ölçümü + LIDT + PLC kilit |
| **7B (`S6.9`) `PT420` Ayrıştırma (`Exp133`)** | `500 mm` uzak valf + `600 mm` He hattı; kenar-kaynaklı `316L` CF63 körük (`k ≤ 6.282 N/m`); `4×` S-ilmek OFHC Cu örgü (`RRR ≥ 200, k ≤ 60 N/m`); `1,4–21 Hz` `25 dB` FF | `k_bellows = 2.000 N/m`, `k_braid = 52,7 N/m` (`ΔT = 3,7 mK`), `σ_stage = 0,1024 nm`, `σ_pointing = 0,1473 nm` (`VC-E`) | Yay sabiti + `20 mK` iletkenlik + PSD |
| **7C (`S6.10` Net) `3 kΩ` `NbTiN` & `4 K` `968`-Kapı (`Exp131`)** | `NbTiN` (`t=9 nm, w=100 nm, L_□=100 pH/□, Z_r=3 kΩ, f_r=5,0 GHz, L_res=300 µm, B_M4=0,1785 T`); `4 K` `SKY130` `968`-kapı çapraz-anahtar (`15,4 mW`); `20-bit` DC dipol DAC | `F_iSWAP = 0,9655–0,9918`, `L=11 FT` `%99,40` perkolasyon, `±0,2 mV` bias | `20 mK` VNA (`0,1785 T`) + `4 K` tarama |

---

## RFQ-08 (`v5.0`) — `S5.6` In-Situ `²⁸Si` UHV MBE Capper + `S6.5/S6.11` `32`-Kanal Cryo-TWPA/HEMT & `ZU48DR Q16.16` BOED-FPGA

- **BOM Referansı:** `S5.6-01..04` (`22,40 kg`, `$67,0k / $95,0k / $145,0k`) + `S6.11-01..04` (`Exp140 S6.5-01..04`, `19,27 kg` [`7,77 kg` soğuk + `11,50 kg` raf], `$456,4k / $629,2k / $925,2k`) — **`8` parça, `41,67 kg`, referans bant `$523,4k / $724,2k / $1.070,2k` (`%13,1` of `M3 v6.0`, `{Liste-Çapası}/{Varsayım}`)**.
- **Aday Tedarikçi Sınıfı:** Lot 8A: Dr. Eberl MBE (`SUSI-63`), CreaTec, Mantis, Scienta Omicron, Inficon, SAES, Isonics; Lot 8B: AMD/Xilinx + HiTech Global (`ZU48DR`), Silent Waves / ArgoQ / SeeQC (TWPA), Low Noise Factory (`LNF-LNC4_8C`), Delft Circuits / Coax Co.

| Alt-Lot & Parça | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | FAT / SAT Doğrulama Yöntemi |
|---|---|---|---|
| **8A (`S5.6-01..04`) Potasız `²⁸Si` MBE, `PBN` Isıtıcı & FG/H (`Exp139`)** | `s5_loadlock` `+Z` `CF100` (`Ø152×280 mm`, min boşluk `≥ 70 mm`); `22,40 kg`; `P_base ≤ 2×10⁻¹⁰`, `P_growth ≤ 5×10⁻¹⁰ Torr`; `<50 ppm ²⁹Si` çubuk (`>1.000` yonga); **`8,0 ± 0,3 nm`**; `345 °C` PBN + `350 °C` FG/H + `80 L/s TMP/NEG` | `P_base=1,5×10⁻¹⁰ Torr`, `0,10 nm/s` (`80 s`), `S_ε=0,390 µeV/√Hz` (`F_ff=%97,70`), `%0` boru-hattı cezası, `0,00 µW` kriyo yük | FAT: QCM + XTEM/ellipsometri + SIMS `²⁹Si < 50 ppm` + `He ≤ 10⁻¹⁰` + RGA |
| **8B (`S6.11-01..04` / `Exp140 S6.5`) `ZU48DR`, `32×` TWPA/HEMT & `96`-Coax** | `2× ZU48DR` `2U` (`11,50 kg`, `Q16.16` `≤ 25 µs/adım`, `abs(ΔRMS) ≤ 1,0 Hz`); `32×` `20 mK` TWPA+Purcell (`2,72 kg`, `T_N ≤ 0,5 K`, `F_RO ≥ 0,995`); `32×` `4 K` HEMT (`1,02 kg`, `≤ 7,8 mW`); `96×` `0,86 mm` coax (`4,03 kg`); toplam `19,27 kg` | `2,336 µs/adım`, `abs(ΔRMS)=0,050 Hz`, `T_N=0,30 K`, `625×` Purcell (`T_1=124,3 ms`), `F_RO=0,9961 @ 2 µs`, `20 mK=6,256 / 14 µW` | FAT: `400`-adaylı `Q16.16 vs FP64` loopback + `20 mK` 32-ton S21/sıkışma + `4 K` HEMT sertifikası |

---

## RFQ-09 (`v6.0` Modüler Opsiyon Paketi) — `Option-Q` (`qRAM` + `S1-Multi` + `1550 nm` Fiber) & `Option-HPC` (`4U` `100G` RoCEv2 RDMA QEC Dekoderi)

- **BOM Referansı (`M3 v5.0 Base` Üzerine Tamamen Modüler — Çift Sayım Yok):**
  - **Lot 9A (`Option-Q`, `Exp142` `s9q_hardware_spec.json`):** `S1.7-01` (`Exp142 S1.6-01`, `4,80 kg`, `$68k`) + `S9.4-01..03` (`Exp142 S9.1-01..03`, `4,40 kg`, `$100k`) → **`4` parça, `9,20 kg`, `$118,0k / $168,0k / $242,0k`** (`{Varsayım}`).
  - **Lot 9B (`Option-HPC`, `Exp143` `s9hpc_hardware_spec.json`):** `S9.HPC-01..03` (`56,00 + 4,20 + 3,80 = 64,00 kg`, `2.195 W` raf / `0,0 W` kriyo) → **`3` parça, `64,00 kg`, `$98,0k / $132,0k / $181,0k`** (`{Liste-Çapası}/{Varsayım}`).
  - **RFQ-09 Toplam:** **`7` parça, `73,20 kg`, `$216,0k / $300,0k / $423,0k`** (`M3 v6.0 Full`'ün `%5,4`'ü; `9-RFQ` toplamı `85` parça, `%77,7` nom / `%92,6` MC varyans).
- **Aday Tedarikçi Sınıfı:**
  - **Lot 9A (`Option-Q`):** VTT / QuTech / SeeQC / STAR Cryoelectronics (`5`-kademe Chebyshev `NbTiN` `50 Ω ↔ 3 kΩ` köprü); Delft Circuits / Bluefors / OZ Optics (`CF63` kriyo-koaks + `1550 nm SMF-28` vakum geçişi & demeti); Orsay Physics / Ionoptika / Tectra / CreaTec (`S1-Multi` `³¹P`/`¹²¹Sb` `450 °C` fırın/`¹⁶⁷Er` kartuş yuvası).
  - **Lot 9B (`Option-HPC`):** NVIDIA (`H100` + `ConnectX-7` `100G` RoCEv2) / AMD (`Alveo U280`) + Supermicro / Dell (`2U` çift-hızlandırıcılı sunucu); Arista / Mellanox-NVIDIA (`1U` cut-through `100 GbE` RoCEv2 optik anahtar + `QSFP28-100G-SR4` + `OM4 MPO-12`); HiTech Global / AMD (`ZU48DR` `100G CMAC` RDMA FW).

### Teknik Şartname & FAT Kabul Tablosu (`RFQ-09` — `Exp142` & `Exp143` Kilitli Parametreleri)

| Alt-Lot & Parça | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | FAT / SAT Doğrulama Yöntemi |
|---|---|---|---|
| **9A (`S9.4-02` / `Exp142 S9.1-02`) `5`-Kademe Chebyshev `NbTiN` `qRAM` Köprüsü** | `20 mK MXC` montaj (`60×30×16 mm`, `0,38 kg`, `S6.5` TWPA altı `≥ 8,5 mm` Z boşluk); `50 Ω ↔ 3 kΩ` `4`-kanal; `4–8 GHz` bandında **`S11 ≤ −20 dB`**, `IL ≤ 0,10 dB`; `20 mK` ısı yükü `≤ 1,5 µW` | `max S11 = −39,56 dB @ 4–8 GHz`, `IL = 0,001 dB`, `BW_20dB = 4,80 GHz` (`3,6–8,4 GHz`), `F_SWAP(³¹P) = 0,9858`, `0,78 µW @ 20 mK` | FAT: `20 mK` 2-port VNA `S11/S21` (`4–8 GHz`) + `50 Ω ↔ 3 kΩ` empedans dönüşümü + termal yük testi |
| **9A (`S9.4-01/03` / `Exp142 S9.1-01/03`) `CF63` `−X` Geçiş & `1550 nm` Fiber Demeti** | `s6_dr_ovc_upper −X` dış port (`100×120×120 mm`, `3,20 kg`, `He ≤ 10⁻¹⁰ mbar·L/s`); `4× NbTi` kriyo koaks + `1× 1550 nm SMF-28` kriyo fiber (`0,82 kg`); `4 K ≤ 0,10 W`, `50 K ≤ 0,80 W` | `100 mK = 6,15 µW`, `4 K = 0,062 W`, `50 K = 0,48 W` (toplam `Option-Q` kriyo payı `< %6` MXC), `1536 nm` `¹⁶⁷Er` optik kayıp `≤ 0,5 dB` | FAT: Helyum kaçak + `1550 nm` OTDR/IL (`300 K → 4 K` soğuma çevrimi) + STEP boşluk kontrolü |
| **9A (`S1.7-01` / `Exp142 S1.6-01`) `S1-Multi` `3`-Türlü Kaynak Kartuşu** | `s1_duoplasmatron +Y` flanş (`76×76×95 mm`, `4,80 kg`, min boşluk `≥ 27 mm`, `≤ 200 W`, `0 W` kriyo); hızlı-değişim `³¹P` gaz / `¹²¹Sb` `450 °C` fırın / `¹⁶⁷Er` mikro-Paul/fırın; `UHV ≤ 10⁻⁹ mbar` | `180 W` tepe, `150 °C` bakeout, mevcut `0,45 T` Wien filtresiyle türler-arası (`³¹P / ¹²¹Sb / ¹⁶⁷Er`) ve `³¹P` izotop ayrımı (`0,991 mm > 0,35 mm`); ağır `¹²¹Sb` (`0,260 mm`) ve `¹⁶⁷Er` (`0,081 mm`) için izotopça zenginleştirilmiş kartuş hammaddesi (`>%99 ¹²¹Sb`, `>%96 ¹⁶⁷Er`) zorunludur (`Exp142`); **`¹⁶⁷Er` `1536 nm` telekom köprüsü** (`F_P,eff = 1.520`, `β_ZPL = 0,9993`) | FAT: `450 °C` fırın vakum gaz-çıkışı (`RGA`) + hızlı kartuş tekrarlanabilirliği (`±0,05 mm`) + Wien kütle taraması |
| **9B (`S9.HPC-01`) `4U` `100G` RoCEv2 RDMA QEC Dekoder Düğümleri** | `2× 2U` (`4U` toplam: `482,6×780×177,8 mm`, `56,00 kg`, `≤ 2.200 W`, `0 W` kriyo); düğüm başı `2× H100/Alveo-U280` + çift-`100G ConnectX-7`; **FAT gecikme: Surface `d=37` `< 6,70 µs` VE `qLDPC [[144,12,12]]` `< 2,62 µs`** | Surface `d=37` uçtan-uca **`6,34 µs`** (`< 6,70 µs` `D3` döngüsü, `16 L/modül`, `100L: 7` modül); **`qLDPC [[144,12,12]]`** uçtan-uca **`2,32 µs`** (`< 2,62 µs`, **`108 L` tek `4U` modülde!**) | FAT: `100G` RoCEv2 loopback ile canlı `d=37` MWPM (`p_det = 0,0426`) & `[[144,12,12]]` BP-OSD stres testi (`0` backlog!) |
| **9B (`S9.HPC-02/03`) `1U` Cut-Through `100 GbE` Köprü, `QSFP28` & `ZU48DR CMAC`** | `1U` cut-through `100 GbE` anahtar + `4× QSFP28-100G-SR4` + `20 m OM4 MPO-12` (`4,20 kg`, `95 W`) + yedekli `2,6 kW` Titanium PSU & `ZU48DR 100G CMAC` FW (`3,80 kg`); tek-yön giriş **`τ_ingest ≤ 0,80 µs`** | `τ_ingest = 0,777 µs` (`0,007 µs` koaks + `0,32 µs` `ZU48DR` IQ/CMAC + `0,45 µs` `100G` RDMA DMA), `4×` `100G` port (`100L d=37` için `25,5 Gbps` → `2` yedekli fiber), toplam `Option-HPC = 64,00 kg / 2.195 W` | FAT: Donanımsal zaman-damgalı (`PTP/White Rabbit`) tek-yön & gidiş-dönüş DMA gecikme histogramı (`p99`) |

### Teklif Soruları (`RFQ-09` — Modüler Bütçe Kontrolü & Filo Ölçeklemesi)
1. *(Lot 9A — `Option-Q`)* `5`-kademe Chebyshev `NbTiN` `50 Ω ↔ 3 kΩ` çipi (`S9.4-02`) ile `CF63` `1550 nm` kriyo-fiber geçişinin (`S9.4-01/03`) `M3 Base` satın almasından bağımsız olarak sonradan sahada takılabilir (`field-upgradeable`) kit fiyatı ve teslim süresi nedir?
2. *(Lot 9B — `Option-HPC`)* Tek `4U` `Option-HPC` modülü (`$132k`, `108 L` `qLDPC` veya `16 L` `d=37` Surface) ile `100 L` Surface `d=37` filosu (`7` modül = `13` düğüm, `14,32 kW`) için toplu alım iskontosu nedir?

---

## Teklif Toplama Sonrası Kapanış Protokolü (`Exp128 v6.0` → Fiziksel Tedarik)

1. Dokuz RFQ'dan (`RFQ-01..RFQ-09`, `85` parça, nominal `%77,7` / MC varyans `%92,6`) gelen bağlayıcı fiyat teklifleri `BOM_DETAILED.csv`'deki `{Model-Kalibrasyon-Exp114}` / `{Varsayım}` hücrelerinin yerine `{Teklif-Çapası}` etiketiyle yazılır (kanonik `BOM.csv` yine değiştirilmez).
2. `experiments/exp128_bom_sensitivity/run_exp128.py` gerçek tekliflerle yeniden koşturulur; özellikle `S6.6` (`RFQ-05`, `%70,0` varyans) `B/C` sınıfı kesinleştirilerek `M3 v6.0 Full` `P(Program > $100M)` (`%4,92 ± %0,07`) ve `FOAK 5y TCO` (`%6,90`) kuyruk riski daraltılır.
3. `$100M` sert bütçe marjı sıkılaşması durumunda **modüler kademeleme** uygulanır: Faz-1 kurulumu **`M3 v5.0 Base` (`$5,25M`, `P>100M = %4,37`)** veya **`256`-hücre Pilot (`$4,79M`)** ile yapılır; **`Option-Q` (`+$168k`)** ve **`Option-HPC` (`+$132k`)** Faz-2'de sahadan takılır.
