# Atom Litografi Makinesi — Ön Tedarikçi Teklif İstem (RFQ) Teknik Şartname Taslağı (`RFQ_SPECIFICATIONS.md` — `v7.3`, `TRL 1–2 / M0`, `UNQUOTED_ROM_ESTIMATE`)

> **Amaç ve Epistemik Kapsam (`procurement_status = UNQUOTED_ROM_ESTIMATE`, `no_supplier_quotes = true`, Sertifikasız `M0` Taslak):** `Exp114` ve `Exp128 v7.0` (`100.000` örneklemli Monte Carlo) sonuçları, maliyet belirsizliğinin fizik modellerinden değil **`B/C` tedarik duvarından** (`$0,59M–$13,07M` kanonik bant; `BOM_DETAILED v7.0` toplam varyansının **`%92,6`'sı** 10 RFQ paketiyle kapsanır) kaynaklandığını göstermiştir. Bu belge, gelecekte gerçek tedarikçilerden bağlayıcı fiyat/teslim teklifi toplamak üzere hazırlanmış **sertifikasız `M0` ön şartname taslağı (`RFQ-01..RFQ-10`)** içerir. **180/180 parçanın tamamı `UNQUOTED_ROM_ESTIMATE` durumundadır: sıfır bağlayıcı tedarikçi teklifi vardır; tüm hedef fiyat bantları `{Model-Kalibrasyon-Exp114}` / `{Liste-Çapası}` / `{Varsayım}` parametrik ROM tahminleridir.** `RFQ-10` bir sertifikasyon belgesi değildir; **SEMI kendi `SEMI S2` kılavuzu için sertifika vermez, `IEC 61508 SIL-3` ise tam emniyet yaşam döngüsü ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir.**

**Tarih:** 2026-11-27 *(`v7.3` engel kapanış senkronu: `OBS-060` 3-kademeli yonga çapı tutarlılığı [FOAK `50 mm` CAD/BOM vs Fab `200 mm` ölçekli TCO], `OBS-061` `UNQUOTED_ROM_ESTIMATE` & tek/duopoli teslim süresi risk kütüğü + Efabless 2025 kapanışı sonrası aktif SkyWater/ChipFoundry/MOSIS/EUROPRACTICE MPW göçü, `OBS-068`/`OBS-079`/`OBS-126` `12 kWh` LFP UPS `202,8 dk @ %90 DoD` + şebeke-tarafı `12,5 kW` PT420 kontaktörü + `±300 A` HTS mıknatıs rampa kolu, `OBS-134` `%5` MBE yakalama verimi ve `>=50 nm` SOI BOX kuyruğu, `OBS-139` `iradina` MEMS sputtering ömrü)*  
**Kapsam:** `BOM_DETAILED.csv v7.0` (`180` parça, `M3 v7.0 Full = $5.692.800` [`Faz-1 Base+Safety = $5.392.800`, `M3 Base = $5.247.800`]) içindeki **`91` kritik parça** — nominal `M3 v7.0 Full` donanım maliyetinin **`%78,2`'si (`$4.454.100`)**, Monte Carlo BOM maliyet varyansının **`%92,6`'sı**! *(Klasik `RFQ-01..06`: `58p / %51,8`; `RFQ-01..08` `v5 Base`: `78p / %70,4`; `RFQ-01..09` `v6 Full`: `85p / %75,7` [`v6 Full`'ün `%77,7`'si].)*

### Tek/Duopoli Tedarik Darboğazı, Teslim Süresi (`P10 / P50 / P90` Hafta) & `UNQUOTED_ROM_ESTIMATE` Risk Kütüğü (`OBS-061`)

| BOM Kimliği | Darboğaz Bileşeni | Piyasa Yapısı & Risk | Teklif Durumu | Teslim (`P10 / P50 / P90` hf) | Aktif Yedek / Risk Azaltma Yolu |
|---|---|---|---|---:|---|
| `S6.8-01` | Bluefors `LD400` / Oxford `Proteox` `20 mK` DR | Duopoli (en uzun kritik yol) | `UNQUOTED_ROM_ESTIMATE` | `36 / 56 / 84` | Paralel Bluefors + Oxford + Leiden RFQ; Faz-1 siparişi T=0 |
| `S6.8-03` | `20 L STP ³He` İzotop Gaz Şarjı | Stratejik tahsis / ihracat kontrolü | `UNQUOTED_ROM_ESTIMATE` | `24 / 44 / 78` | Çift kaynaklı tahsis niyet mektubu (LOI) + kapalı-devre GHS |
| `S5.4-01` / `S5.6-02` | `²⁸SiH₄` (`>99,95%`) Epi & `<50 ppm ²⁹Si` MBE Çubuk | Tek/duopoli izotop zenginleştirme | `UNQUOTED_ROM_ESTIMATE` | `26 / 48 / 78` | FOAK `Ø50 mm` kupon (düşük kütle); `%5` MBE verimiyle erken çubuk stoğu |
| `S2.4-01` / `S7.3-01` / `S6.10-03` | `SKY130` Blanker & `4 K` Kontrol MPW Şatılı | **Efabless 2025 kapanışı** — aracı göçü | `UNQUOTED_ROM_ESTIMATE` | `20 / 32 / 48` | **Aktif aracılar:** SkyWater doğrudan / ChipFoundry / TinyTapeout / MOSIS / EUROPRACTICE |
| `S6.6-01` / `S6.11-02` | `4 K` InP HEMT LNA & `20 mK` `Nb/AlOx/Nb` TWPA | Duopoli / özel süperiletken dökümhane | `UNQUOTED_ROM_ESTIMATE` | `24 / 40 / 68` | LNF/CMT/B&Z teklif kilidi (`RFQ-05`) + ayrı TWPA NRE bütçesi (`Exp134`) |
| `S6.3-01..05` | `8`-Bobin `1,50 T` Mıknatıs & `±300 A` HTS Uçlar | Özel kriyo-mıknatıs üreticileri | `UNQUOTED_ROM_ESTIMATE` | `28 / 46 / 72` | Cryomagnetics / AMI / Oxford / Cryogenic Ltd. paralel teklif |
| `S2.1..S2.3` | `32×32` SOI/TSV MEMS Apertür, Blanker, Mini-Lens | Özel MEMS dökümhane NRE | `UNQUOTED_ROM_ESTIMATE` | `16 / 30 / 52` | Fraunhofer IPMS/ISIT, CEA-Leti, VTT, IMT; `S9.3-01` SiC/W koruyucu kaplama |
| `S6.1-02` / `S7.SAFETY-04` | `PT420` (`12,5 kW`) & `15 kVA / 12 kWh` LFP UPS | Ticari COTS (şebeke-tarafı kontaktör) | `UNQUOTED_ROM_ESTIMATE` | `10 / 18 / 28` | Cryomech CPA1110 + Eaton 9PX / Vertiv GXT5 `12 kWh` LFP (`202,8 dk @ %90 DoD`) |

> **Yonga Çapı Kademe Uyumluluğu (`OBS-060`):** `cad/params.py` ve `BOM_DETAILED.csv` (`S5.4-01`, `$56k / 25 yonga = $2.240/yonga`) **`Ø50 mm` FOAK R&D prototipine** kilitlidir (`80×80 mm` taşıyıcı, `Ø150 mm` mıknatıs açıklığı). Fab-ölçeği `200 mm` (`16×` alan) ve `300 mm` (`36×` alan) yonga ekonomisi (`Exp134`/`Exp141`), `≥Ø300 mm` mıknatıs/kriyostat ve yük-kilidi yeniden tasarım CAPEX ekleriyle açıkça ayrıştırılmıştır.

| RFQ Kodu | Alt Sistem & BOM Kimlikleri | Paket Kapsamı | `M3 v7.0` Referans Bant (`P10 / P50 / P90`) | `M3 v7` Nom Payı | MC Varyans Etkisi |
|---|---|---|---:|---:|---|
| **RFQ-01** | `S1.1, S1.2, S1.3, S1.5, S1.6` | Duoplazmatron (`³¹P⁺/²⁹Si⁺`), Wien (`0,45 T`), `Arch-B` `10→5 keV` kolon, `HDA-HiRes` (`0,453 eV`) & `PH₃` kabin | `$228k / $398k / $731k` | `%7,0` | `Exp124` kolon + güvenlik |
| **RFQ-02** | `S2.1, S2.2, S2.3` | MEMS Apertür, Blanker & `Arch-B` Mini-Lens Dizisi (`0,50 mm`, `32×32 = 1.024`, `WD=0,250 mm, σ=1,428 nm`) | `$330k / $661k / $1.387k` | `%11,6` | **#2 Varyans sürücüsü (`%5,9`)** |
| **RFQ-03** | `S4.3, S4.4` | `6-DOF` UHV Kaba+İnce Piezo Kademe (`σ≤0,5 nm`) & 3-Eksen Lazer İnterferometre (`pm`) | `$101k / $163k / $283k` | `%2,9` | Konum hata bütçesi çekirdeği |
| **RFQ-04** | `S6.3` | `8`-Bobinli `1,50 T` / `0,1785 T` (`17,8 ppm`) Kriyo-Mıknatıs & `Nb RRR>300` Kalkan (`22,3 µT`) | `$106k / $185k / $340k` | `%3,3` | Risk `R7` (`Exp125`) donanım kapanışı |
| **RFQ-05** | `S6.6` (`S6.6-01..07`) | `56–82` Zincir `4 K` InP HEMT LNA (`≤2,8 mW`), Kriyo İzolatör/Koaksiyel + `9000`-ch `NbTiN` Rezonatör | `$409k / $765k / $1.418k` | `%13,5` | **#1 Varyans sürücüsü (`%69,5` — `B/C` duvarı!)** |
| **RFQ-06** | `S6.8 + S6.1` | Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı (`³He/⁴He` GHS) + `PT420` `4 K` Ön-Soğutucu | `$472k / $779k / $1.338k` | `%13,7` | **#3 Varyans sürücüsü (`%5,3`, en uzun teslim)** |
| **RFQ-07 (`v4.0` Net)** | `S5.5 + S6.9 + S6.10` *(net)* | `S5.5` `808 nm` Flaş (`43,49 J/cm²`) + `S6.9` `PT420` Uzak Valf/Körük/Örgü + `S6.10` `3 kΩ` `NbTiN` & `4 K` `968`-Kapı | `$187k / $334k / $621k` | `%5,9` | **#5 Varyans sürücüsü (`%2,7`)** |
| **RFQ-08 (`v5.0`)** | `S5.6 + S6.11` (`Exp140 S6.5`) | `S5.6` In-Situ `²⁸Si` UHV MBE + FG/H (`22,40 kg`, `$95k`) + `S6.5/S6.11` `32`-ch TWPA/HEMT + `ZU48DR` (`19,27 kg`, `$629,2k`) | `$523k / $724k / $1.070k` | `%12,7` | **#4 Varyans sürücüsü (`%3,3`)** |
| **RFQ-09 (`v6.0` Modüler)** | `S1.7 + S9.4 + S9.HPC` | `Option-Q` (`9,20 kg`, `$168k`: Chebyshev `qRAM` + `S1-Multi` + `1550 nm` fiber) & `Option-HPC` (`64,00 kg`, `$132k`: `4U` `100G` RDMA) | `$216k / $300k / $423k` | `%5,3` | Modüler opsiyon (`%0,8` var.) |
| **RFQ-10 (`v7.0` Ön Emniyet)** | **`S7.SAFETY-01..06`** | **`Exp150` sertifikasız `M0` ön emniyet tasarım taslağı (`SEMI S2`/`SIL-3` mimari hedef referanslı; `355,0 kg`, `1.090 W`, `0 W` kriyo):** `SDS PH₃` + `OD8`/`3 mm` çelik X-ışını kılıf + `1oo2D` PLC/Crowbar hedefi + `15 kVA` UPS + `O₂`/`DN50` + `80 ms` UHV vana | **`$92k / $145k / $220k`** | **`%2,5`** | **Ön emniyet bütçe hedefi (`%0,5` var.; sertifikasız `M0`)** |
| **TOPLAM (`v7.0 Full`)** | **91 Kritik Parça** | **10 Stratejik Tedarik Paketi (`RFQ-01..RFQ-10`)** | **`$2,66M / $4,45M / $7,83M`** | **`%78,2`** | **Toplam BOM MC Varyansının `%92,6`'sı** |

---

## RFQ-01 — İyon Kaynağı, `10→5 keV` Yavaşlatma Kolonu, `HDA-HiRes` Enerji Süzgeci & `PH₃` Gaz Güvenliği (`S1.1, S1.2, S1.3, S1.5, S1.6`)

- **BOM Referansı:** `S1.1-01..05`, `S1.2-01..04`, `S1.3-01..05`, `S1.5-01..03`, `S1.6-01..02` (`19` parça; `$227,5k / $398,0k / $730,5k`).
- **Aday Tedarikçi Sınıfı:** Orsay Physics, Raith, Ionoptika, Specs, Tectra, Hiden/Kimball + CS Clean Solutions, Edwards, Entegris, Matheson.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **İyon Türleri & Enerji (`Exp124`)** | `³¹P⁺` (baz) + ops. `²⁹Si⁺`; çıkarım `10–15 keV` → yavaşlatma `5,0–20,0 keV` | `V_extract = 10 keV`, `V_land = 5,000 keV`, kolon `562,66 mm` | HV bölücü + retarding analizör |
| **Parlaklık & `HDA-HiRes` (`S1.5`)** | Net `B ≥ 7,22×10⁴ A/m²/sr`; `ΔE_FWHM ≤ 0,50 eV` (`Arch-B C_c = 2,660 mm`) | `HDA-HiRes R₀ = 40 mm, ΔE_FWHM = 0,453 eV` | Çift-apertür Faraday + enerji taraması |
| **Wien (`S1.2`) & Yavaşlatma (`Arch-B`)** | `m/Δm ≥ 60`; `WD = 0,250 mm`, `E_gap ≤ 12 MV/m` (`10,60 MV/m`) | `B = 0,45 T, L = 150 mm`, `σ_spot = 1,428 nm` | Kütle tarama FWHM + knife-edge |
| **HV, Vakum & `PH₃` (`S1.6` + `RFQ-10`)** | `ΔV/V ≤ 10⁻⁴`, CF100 `≤ 10⁻⁹ mbar`, `150 °C` bakeout; `RFQ-10` SDS `<650 Torr` uyumlu | `≤ 5×10⁻¹⁰ mbar`, `< 0,02 ppm` alarm | RGA, `He ≤ 10⁻¹⁰`, PLC kilit testi |

---

## RFQ-02 — MEMS Çok-Demet Apertür, Elektrostatik Blanker & `Arch-B` Mini-Lens Dizisi (`S2.1, S2.2, S2.3`)

- **BOM Referansı:** `S2.1-01..04`, `S2.2-01..04`, `S2.3-01..04` (`12` parça; `$329,5k / $661,0k / $1.387,0k`).
- **Aday Tedarikçi Sınıfı:** IMS Nanofabrication ekosistemi, Fraunhofer IPMS/ISIT, CEA-Leti, LioniX, VTT, IMT Masken.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Dizi Ölçeği & Eş-Adım (`Arch-B`)** | `32×32 = 1.024` demetcik, **`0,50 mm` eş-adım** (`16,0×16,0 mm < Ø28,0 mm`), `16×` 64-ch karo | `≥ %98` çalışan demetcik verimi | SEM CD + otomatik süreklilik taraması |
| **Apertür, Blanker & Mini-Lens** | `30 µm` SOI (`±50 nm` CD), `V_blank ≤ 35 V`, kapı `≤ 1 ms`, `f₁ ≥ 1,0 MHz` (`2,59 MHz`), `σ_spot ≤ 1,50 nm` | `σ_spot = 1,428 nm`, `10 µs` kapı, `3 kV` hi-pot | LDV, interferometri, knife-edge |
| **Interposer & Vakum** | `LTCC/AlN` + TSV fan-out (`1.024` ch), UHV `≤ 10⁻⁹ mbar`, `150 °C` bakeout | Tak-çıkar tekrarlanabilirlik `±2 µm` | RGA + kinematik metroloji |

---

## RFQ-03 — `6-DOF` UHV Piezo Kademe & 3-Eksen Lazer İnterferometri (`S4.3, S4.4`)

- **BOM Referansı:** `S4.3-01..04`, `S4.4-01..04` (`8` parça; `$100,5k / $163,0k / $282,5k`).
- **Aday Tedarikçi Sınıfı:** Physik Instrumente (PI PIMars UHV), SmarAct, Attocube; Renishaw (`XL-80`/`RLE`), Zygo, Attocube IDS.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Artık Titreşim & Kademe (`Exp79/133`)** | `6-DOF`, XY `≥ 200 µm` + kaba `±25 mm`, `σ_kademe ≤ 0,50 nm` RMS (`VC-E` zemin) | `σ_stage = 0,1024 nm` (`Exp133 CFG4`) | Kapalı-çevrim interferometre PSD |
| **İnterferometre & Arayüz (`S4.4`)** | 3-eksen diferansiyel (`≤ 0,05 nm`), `μ_r < 1,01`, UHV `≤ 10⁻⁹ mbar`, gecikme `< 5 µs` | `10 pm`, `±0,05 ppm`, `< 1 µs` EtherCAT/SPI | Sabit ayna sürüklenme + osiloskop |

---

## RFQ-04 — `8`-Bobinli `1,50 T` / `0,1785 T` Kriyo-Mıknatıs & `Nb (RRR>300)` Kalkan (`S6.3`, `Exp125/131`)

- **BOM Referansı:** `S6.3-01..05` (`5` parça; `$106,0k / $185,0k / $340,0k`).
- **Aday Tedarikçi Sınıfı:** Cryomagnetics, American Magnetics (AMI), Oxford Instruments NanoScience, Cryogenic Ltd., Janis/Lake Shore.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Bobin & Çift-Kip Alan (`Exp125/131`)** | `8`-bobin (`Ø150` bore / `36 mm` yarık / `Ø352` OD); `0,15–1,50 T` (`1,500 T` ESR + `0,1785 T` `M4`) | `17,8 ppm`, `I/I_c = 0,212`, `σ_hoop = 52,7 MPa` | `4,2 K` NMR / 3-eksen Hall haritası |
| **Kalkan, `4 K` Yük & Quench** | `Nb (RRR>300)` + `Cryoperm-10`: `B_res ≤ 0,40 T`; `4 K ≤ 100 mW`; quench `≤ 100 K` (`1,563 Ω` dump uyumlu) | `B_res = 22,3 µT`, `T_quench = 64,6 K`, `18,94 kJ` | Hall taraması + FAT quench testi |

---

## RFQ-05 — Fab Okuma Zinciri: `56×` Kriyo-LNA (`≤ 2,8 mW`), İzolatör/Koaksiyel & `9000`-ch `NbTiN` (`S6.6`) — **`B/C` Tedarik Belirsizliği Sürücüsü**

- **BOM Referansı:** `S6.6-01..07` (`7` parça; `$409,0k / $765,4k / $1.418,2k`; BOM MC varyansının **`%69,5`'i**).
- **Aday Tedarikçi Sınıfı:** Low Noise Factory (LNF), CMT, B&Z; LNF/Quinstar/QMC; Delft Circuits, Bluefors; AMD (`ZCU216`); VTT/QuTech/SeeQC.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Zincir & `4 K` LNA (`Exp111/112/113`)** | `56–82` zincir (`NL=110–160`), `P_DC ≤ 7,8 mW` (`PT420`) / `≤ 2,8 mW` (`PT410`), `T_n ≤ 4,0 K` | `≤ 2,1 mW`, `T_n ≤ 2,0 K`, `≥ 38 dB`, `IP3 ≥ −40 dBm` | `4 K` Y-faktörü + iki-ton IMD3 |
| **İzolatör, Koaksiyel, `NbTiN` & RFSoC** | İzolasyon `≥ 20 dB`, `NbTi` `< 0,1 dB/m`, `NbTiN` `Q_i ≥ 10⁵ @ ≤0,4 T`, `14× ZCU216` | `≥ 35 dB`, `Q_i ≥ 2×10⁵`, `8` hat/kart ops. | `20 mK` VNA çentik + SFDR `> 60 dBc` |

---

## RFQ-06 — Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı & `PT420` Ön-Soğutucu (`S6.8 + S6.1`)

- **BOM Referansı:** `S6.8-01..04`, `S6.1-01..03` (`7` parça; `$471,5k / $778,5k / $1.337,5k`).
- **Aday Tedarikçi Sınıfı:** Bluefors (`LD400/XLD`), Oxford Instruments (`Proteox`), Leiden Cryogenics, FormFactor/Janis.

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Kriyo Güç & `³He` GHS (`Exp110/121/140`)** | `T_base ≤ 20 mK`, `≥ 250 µW @ 100 mK` (`LD400`: `14 µW @ 20 mK`), `PT420 ≥ 1,5 W @ 4,2 K` | `≤ 12 mK`, `400 µW @ 100 mK`, `2,0 W @ 4,2 K` | Isıtıcı yük eğrisi + 72s burn-in |
| **Arayüzler (`RFQ-04/07/08/09/10`)** | `≥ 120` fab + `96` `S6.5` koaks + `−X CF63` `Option-Q` + **`ASME DN50 0,5 barg` OVC tahliye** | Kuru He `1,098 m³` STP (`60 m³` oda `O₂=%20,57`) | STEP ICD + ASME basınç/kaçak |

---

## RFQ-07 (`v4.0` Net) — `S5.5` Flaş-Tavlama Optik Kafası, `S6.9` `PT420` Ayrıştırma & `S6.10` `M4` `3 kΩ` `NbTiN` / `4 K` Çapraz-Anahtar

- **BOM Referansı (`v5.0+` Net):** `S5.5-01..04` (`$95k`), `S6.9-01..04` (`$68k`), `S6.10-01/03/04` (`$171k` net) — **`12` satır (`11` fiyatlı), `$187,0k / $334,0k / $621,0k` (`{Varsayım}`)**.

| Alt-Lot & Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **7A (`S5.5`) `808 nm` Flaş & Safir (`Exp130/139`)** | `808 nm` qCW `43,49 J/cm² / 1,0 ms` (`1530,1 K`, `8,96× LIDT`), `+Y` CF63 safir (`Ø44 mm CA`), `10 µs` pirometre | `%99,99` `{311}` çözünmesi, `σ_anneal = 0,430 nm` (`RFQ-10` `OD8` çelik kılıf uyumlu) | Enerji/profil + LIDT + PLC kilit |
| **7B (`S6.9`) `PT420` Ayrıştırma (`Exp133`)** | `500 mm` uzak valf + `600 mm` He hattı; CF63 körük (`k ≤ 6.282 N/m`); `4×` OFHC örgü (`k ≤ 60 N/m`); `25 dB` FF | `k_bellows = 2.000 N/m`, `k_braid = 52,7 N/m`, `σ_stage = 0,1024 nm` | Yay sabiti + `20 mK` iletkenlik |
| **7C (`S6.10` Net) `3 kΩ` `NbTiN` & `4 K` `968`-Kapı** | `NbTiN` (`Z_r=3 kΩ, f_r=5,0 GHz, L_res=300 µm, B_M4=0,1785 T`); `4 K` `SKY130` `968`-kapı; `20-bit` DC DAC | `F_iSWAP = 0,9655–0,9918`, `L=11 FT` `%99,40` perkolasyon | `20 mK` VNA + `4 K` tarama |

---

## RFQ-08 (`v5.0`) — `S5.6` In-Situ `²⁸Si` UHV MBE Capper + `S6.5/S6.11` `32`-Kanal Cryo-TWPA/HEMT & `ZU48DR Q16.16` BOED-FPGA

- **BOM Referansı:** `S5.6-01..04` (`22,40 kg`, `$95k`) + `S6.11-01..04` (`Exp140 S6.5`, `19,27 kg`, `$629,2k`) — **`8` parça, `41,67 kg`, `$523,4k / $724,2k / $1.070,2k`**.

| Alt-Lot & Parça | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | FAT / SAT Doğrulama Yöntemi |
|---|---|---|---|
| **8A (`S5.6-01..04`) Potasız `²⁸Si` MBE & FG/H (`Exp139`)** | `+Z CF100` (`22,40 kg`, `≥ 70 mm` boşluk); `P_base ≤ 2×10⁻¹⁰ Torr`; `<50 ppm ²⁹Si`; **`8,0 ± 0,3 nm`**; `345 °C` PBN + `%5 H₂/N₂` | `0,10 nm/s` (`80 s`), `S_ε=0,390 µeV/√Hz` (`F_ff=%97,70`), `0,00 µW` kriyo | FAT: QCM + XTEM + SIMS + RGA |
| **8B (`S6.11-01..04` / `S6.5`) `ZU48DR`, `32×` TWPA/HEMT** | `2× ZU48DR` (`11,50 kg`, `≤ 25 µs/adım`, `≤ 1 Hz`); `32×` TWPA+Purcell (`2,72 kg`, `F_RO ≥ 0,995`); `32×` HEMT (`1,02 kg`); `96×` coax (`4,03 kg`) | `2,336 µs/adım`, `abs(ΔRMS)=0,050 Hz`, `625×` Purcell, `20 mK=6,256 / 14 µW` | FAT: `400`-aday `Q16.16` loopback + `20 mK` S21 |

---

## RFQ-09 (`v6.0` Modüler) — `Option-Q` (`qRAM` + `S1-Multi` + `1550 nm` Fiber) & `Option-HPC` (`4U` `100G` RoCEv2 RDMA QEC Dekoderi)

- **BOM Referansı (`M3 Base` Üzerine Tamamen Modüler):** `S1.7-01` + `S9.4-01..03` (`Option-Q`, `9,20 kg`, `$118k/$168k/$242k`) + `S9.HPC-01..03` (`Option-HPC`, `64,00 kg`, `$98k/$132k/$181k`) — **`7` parça, `73,20 kg`, `$216,0k / $300,0k / $423,0k`**.

| Alt-Lot & Parça | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | FAT / SAT Doğrulama Yöntemi |
|---|---|---|---|
| **9A (`S9.4-01..03` & `S1.7-01`) `Option-Q` (`Exp142`)** | `5`-kademe Chebyshev `NbTiN` `50 Ω↔3 kΩ` (`S11 ≤ −20 dB`, `≤ 1,5 µW @ 20 mK`); `−X CF63` + `1550 nm SMF-28`; `S1-Multi` `³¹P/¹²¹Sb/¹⁶⁷Er` (`4,80 kg`) | `max S11 = −39,56 dB @ 4–8 GHz`, `F_SWAP(³¹P) = 0,9858`, `0,78 µW @ 20 mK`, `¹⁶⁷Er 1536 nm` (`F_P,eff = 1.520`) | FAT: `20 mK` VNA `S11/S21` + `1550 nm` OTDR + `450 °C` RGA |
| **9B (`S9.HPC-01..03`) `4U` `100G` RoCEv2 RDMA (`Exp143`)** | `2× 2U` (`4U`, `64,0 kg`, `2.195 W`, `0 W` kriyo); `4× QSFP28-100G`; **FAT: Surface `d=37` `< 6,70 µs` VE `qLDPC` `< 2,62 µs`**; `τ_ingest ≤ 0,80 µs` | `τ_ingest = 0,777 µs`; `d=37` **`6,34 µs`** (`16 L/modül`); **`qLDPC [[144,12,12]]` `2,32 µs`** (`108 L` tek `4U` modülde!) | FAT: `100G` RoCEv2 canlı MWPM & BP-OSD loopback (`0` backlog) |

---

## RFQ-10 (`v7.0` Ön Emniyet Tasarım Taslağı — Sertifikasız `M0`) — `SEMI S2` / `ANSI Z136.1` / `IEC 61508 SIL-3` Hedef Referanslı Paket (`S7.SAFETY-01..06`)

> **Sertifikasyon Sınırı:** Bu paket sertifikasız `M0` ön şartname taslağıdır (`no_supplier_quotes = true`). **SEMI kendi `SEMI S2` kılavuzu için sertifika vermez; `IEC 61508 SIL-3` ise tam emniyet yaşam döngüsü ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir.** Tablodaki `SIL-3` / `SIL-2` sınıfları yalnızca tedarikçi bileşen ve sistem tasarım hedeflerini belirtir.

- **BOM Referansı (`Exp150` `s_safety_spec.json` Birebir):** `S7.SAFETY-01..06` — **`6` kalem, `355,0 kg` harici temizoda tesis yükü (`CAD v6.0` nominal şasi kütlesi `1.108,137 kg` değişmez), `1.090,0 W` sürekli güç, `0,0 W` kriyo yükü, `$92,0k / $145,0k / $220,0k` (`M3 v6.0 Full`'ün `%2,61`'i; `{Liste-Çapası}/{Varsayım}`)**.
- **Aday Tedarikçi Sınıfı:** Entegris (`SDS` sub-atm `PH₃`) / CS Clean Solutions / Honeywell Analytics (`S7.SAFETY-01`); Lasermet / Kentek / Thorlabs + özel CNC `316L` (`S7.SAFETY-02`); Pilz (`PNOZmulti`/`PSS 4000`) / Siemens `S7-1500F` (`SIL-3` hedef `1oo2D` PLC bileşen sınıfı) + Ross Engineering HV crowbar (`S7.SAFETY-03`); Eaton `9PX` / Vertiv `Liebert GXT5` `15 kVA LFP` (`S7.SAFETY-04`); Teledyne / MSA `O₂` + BS&B `ASME DN50` + Ohmite `1,563 Ω` (`S7.SAFETY-05`); VAT `80 ms` yay-dönüşlü UHV vana + Fluke `451P` (`S7.SAFETY-06`).

### Ön Teknik Şartname & FAT Kabul Hedefleri (`RFQ-10` — `Exp150` Model Sınırları, Sertifikasız `M0`)

| Parça & Referans Standart | Zorunlu Alt/Üst Sınır (Taslak) | Model Hedef Değeri | Gelecek FAT / Bağımsız Değerlendirme Yöntemi |
|---|---|---|---|
| **`S7.SAFETY-01` `SDS PH₃` Kabin & Scrubber (`SEMI S2/S8` ref., `SIL-3` hedefi)** | Sub-atm `SDS` mikro-tüp (`< 650 Torr`, `≤ 10 g` envanter), çift-ceketli vakum hattı, `≥ 250 CFM` kuru yıkayıcı (`≥ %99,9` verim), çift `0,02 ppm` L1 / `0,05 ppm` L2 kesme hedefi (`≤ 15 s`); `118,0 kg`, `480 W` | Model operatör maruziyeti **`0,00715 ppm << 0,05 ppm`** ACGIH TLV-TWA (`7×` marj, `12,0 s` kesme) | FAT: üçüncü-taraf `SEMI S2` değerlendirmesi + `250 CFM` debi + `0,02/0,05 ppm` gaz kilit testi |
| **`S7.SAFETY-02` `OD8` + `3 mm` Çelik Lazer/X-Işını Kılıf (`ANSI Z136.1` ref., `SIL-3` hedefi)** | `S5.5 +Y` pencere çevresi (`280×260×220 mm`, `38,0 kg`, `45 W`): `808 nm` `OD ≥ 8` (`111,3 J / 1 ms`) **VE `3 mm` çelik X-ışını zırhı** (`22 keV` `< 0,01 µSv/h`); çift-kanallı mekanik perde **`< 5,0 ms`** hedefi | `OD8` Sınıf-1 kapalı kutu hedefi (`NOHD 1.472 m → 0 m`), çıplak safir `10,11 µSv/h` → **`1,19×10⁻²³ µSv/h`**, **`3,2 ms`** `1oo2D` perde tepkisi | FAT: `808 nm` OD bileşen belgesi + `22 kV` X-ışını doz taraması (`< 0,01 µSv/h`) + osiloskopla `< 5 ms` perde testi |
| **`S7.SAFETY-03` `1oo2D` PLC, E-Stop & `2 MΩ` HV Crowbar (`IEC 61508 SIL-3` hedefi)** | `3U` `1oo2D` `SIL-3` bileşen sınıfı emniyet PLC (`18,0 kg`, `120 W`), `4×` E-Stop mantarı, kapak anahtarları, aktif `2 MΩ` HV crowbar (`E_dep ≤ 0,5 J`, `22 kV → <50 V` **`< 50 ms`**) | `E(10/22 kV) = 0,075 / 0,363 J < 0,5 J`, boşalım **`18,26 ms < 50 ms`**; `25`-satırlı ön FMEA `max RPN 280 → 42 ≤ 60` | Bağımsız fonksiyonel emniyet değerlendirmesi (IEC 61508 yaşam döngüsü) + `22 kV` crowbar deşarj osilogramı |
| **`S7.SAFETY-04` `15 kVA / 12 kWh` Online LFP UPS (`SIL-2` hedefi)** | Çift-dönüşümlü online `15 kVA / 13,5 kW`, `12 kWh` LFP akü (`10,8 kWh @ %90 DoD`), **`0,0 ms` geçiş**, şebeke-tarafı kontaktör (`12,5 kW` PT420 UPS önünde atılır, pik UPS yükü `5,38 kW ≤ 13,5 kW`), tam yük `≥ 30 dk`, Tier-1 (`2,533 kW` + `350 W` kayıp + `120 s` `650 W` mıknatıs rampa-indirme) **`≥ 180 dk @ %90 DoD`**; `145,0 kg`, `350 W` | **`42,2–43,2 dk`** tam yük, **`202,8 dk`** Tier-1 `@ %90 DoD` (eski `10 kWh`: `170,6 dk < 180 dk` yetersizdi), şebeke-tarafı kontaktör + kademeli yük-atma PDU (`S6.3-05` `±300 A` rampa-indirme & `S9.HPC` güvenli kapatma) | FAT: Şebeke kesinti (`0 ms` dalga formu) + `13,5 kW` yük bankası `≥ 30 dk` ve `%90 DoD` `≥ 180 dk` deşarj testi |
| **`S7.SAFETY-05` `O₂` ODH, `ASME DN50` & `1,563 Ω` Quench (`SIL-3` hedefi)** | Temizoda `O₂` monitörü (`%19,5` alarm), `ASME VIII DN50 0,5 barg` OVC patlama diski/tahliye (`≥ 5×` marj), `1,563 Ω` quench boşaltma direnci (`≤ 55 °C`); `24,0 kg`, `35 W` | Kuru `LD400+PT420` (`60 m³` oda `O₂ = %20,57`), `ASME DN50` **`16,37× He / 25,72× N₂`** marj, `18,94 kJ` quench **`38,15 °C < 55 °C`** | FAT: `%19,5 O₂` test gazı + `ASME` `0,5 barg` disk belgesi + `18,94 kJ` termal darbe testi |
| **`S7.SAFETY-06` `80 ms` UHV Sürgülü Vana, `%5 H₂/N₂` Orifis & Dozimetre (`SIL-2` hedefi)** | Yay-dönüşlü fail-close UHV sürgülü vana aktörleri **`≤ 80 ms`** (`Si(100)` oksitlenme `< 0,01 ML`), `ISO 10156` `%5 H₂/N₂` akış sınırlayıcı, kalibreli X-ışını dozimetresi; `12,0 kg`, `60 W` | **`80,0 ms`** kapanma → `Si(100)` oksitlenme **`6,0×10⁻⁴ ML << 0,01 ML`**, `ISO 10156` yanıcı-olmayan karışım sınırı | FAT: Güç-kesme vana kapanma süresi (`≤ 80 ms`) + `NIST/PTB` dozimetre kalibrasyon belgesi |

---

## Teklif Toplama Sonrası Kapanış & Fazlı Bütçe Protokolü (`Exp128 v7.0` → Fiziksel Tedarik)

1. On RFQ'dan (`RFQ-01..RFQ-10`, `91` parça, nominal `%78,2` / MC varyans `%92,6`) gelen bağlayıcı fiyat teklifleri `BOM_DETAILED.csv`'ye `{Teklif-Çapası}` etiketiyle işlenir (kanonik `BOM.csv` asla değiştirilmez).
2. **`$100M` Bütçe Tavanı için Fazlı Dağıtım (Exp128 v7.0 Model Bulgusu):** Tek seferde tam `v7.0 Full` (`$5,693M`) stokastik Program kuyruğu `%5,22` (`> %5`) verdiğinden, **Faz-1 kurulumu `M3 Base + Safety` (`$5,393M`, `173` parça — sertifikasız `M0` ön emniyet kiti tasarım hedefli, `P(Prog>$100M) = %4,67 < %5`, `CU3 PASS`)** ile planlanır; `RFQ-05` (`S6.6 B/C` duvarı) teklifiyle maliyet belirsizliği daraltıldıktan sonra **Faz-2'de `RFQ-09` (`Option-Q + Option-HPC`, `+$300k`)** eklenir ve üçüncü-taraf `SEMI S2` / `IEC 61508` saha değerlendirmesi laboratuvar kurulumunda tamamlanır.
