# Atom Litografi Makinesi — Tedarikçi Teklif İstem (RFQ) Teknik Şartnameleri (`RFQ_SPECIFICATIONS.md` — `v4.0`)

> **Amaç ve Epistemik Kapsam:** `Exp114` ve `Exp128 v4.0` (`100.000` örneklemli Monte Carlo) sonuçları, maliyet belirsizliğinin artık fizik modellerinden değil **`B/C` tedarik duvarından** (`$0,59M–$13,07M` kanonik bant; `BOM_DETAILED v4.0` toplam varyansının **`%92,6`'sı** 7 RFQ paketiyle kapsanır) kaynaklandığını göstermiştir. Bu belge, içeriden daha fazla varsayım üretmek yerine gerçek tedarikçilerden bağlayıcı fiyat/teslim teklifi toplamak üzere hazırlanmış **7 teknik RFQ paketi (`RFQ-01..RFQ-07`)** içerir. **Aşağıdaki hedef fiyat bantları gerçek teklif değil, `Exp114/128/134` `{Model-Kalibrasyon-Exp114}` / `{Liste-Çapası}` / `{Varsayım}` referans bütçeleridir.**

**Tarih:** 2026-11-23 *(`v4.0` yükseltmesi: `RFQ-07` eklendi — `Exp130`, `Exp131`, `Exp133` kilitli şartnameleri)*  
**Kapsam:** `BOM_DETAILED.csv v4.0` (`159` parça, `M3 v4.0 = $4.609.600`) içindeki **`70` kritik parça** — nominal `M3 v4.0` donanım maliyetinin **`%72,9`'u (`$3.358.900`)**, Monte Carlo BOM maliyet varyansının **`%92,6`'sı**! *(Klasik `RFQ-01..06`: `58` parça, `$2.950.900` [`%64,0` nom], `%89,2` varyans.)*

| RFQ Kodu | Alt Sistem & BOM Kimlikleri | Paket Kapsamı | `M3 v4.0` Referans Bant (`P10 / P50 / P90`) | `M3 v4.0` Nom Payı | MC Varyans Etkisi |
|---|---|---|---:|---:|---|
| **RFQ-01** | `S1.1, S1.2, S1.3, S1.5, S1.6` | Duoplazmatron (`³¹P⁺/²⁹Si⁺`), Wien (`0,45 T, 150 mm`), `Arch-B` `10→5 keV` kolon, `HDA-HiRes` (`R₀=40 mm, 0,453 eV`) & `PH₃` kabin/yıkayıcı | `$228k / $398k / $731k` | `%8,6` | `Exp124` kolon + güvenlik kilidi |
| **RFQ-02** | `S2.1, S2.2, S2.3` | MEMS Apertür, Blanker & `Arch-B` Mini-Lens Dizisi (`0,50 mm` eş-adım, `32×32 = 1.024` demetcik, `16×` karo, `WD=0,250 mm, σ=1,428 nm`) | `$330k / $661k / $1.387k` | `%14,3` | **#2 Varyans sürücüsü (`%6,0`)** |
| **RFQ-03** | `S4.3, S4.4` | `6-DOF` UHV Kaba+İnce Piezo Kademe (`σ≤0,5 nm`) & 3-Eksen Lazer İnterferometre (`pm`) | `$101k / $163k / $283k` | `%3,5` | Konum hata bütçesi çekirdeği |
| **RFQ-04** | `S6.3` | `8`-Bobinli `1,50 T` (`Ø150` bore / `36 mm` yarık / `Ø352` OD, `17,8 ppm`) Kriyo-Mıknatıs & `Nb RRR>300` Kalkan (`22,3 µT`) | `$106k / $185k / $340k` | `%4,0` | Risk `R7` (`Exp125`) donanım kapanışı |
| **RFQ-05** | `S6.6` (`S6.6-01..07`) | `56–82` Zincir `4 K` InP HEMT LNA (`≤2,8 mW`), Kriyo İzolatör/Koaksiyel + `9000`-ch `NbTiN` Rezonatör | `$409k / $765k / $1.418k` | `%16,6` | **#1 Varyans sürücüsü (`%73,4` — `B/C` duvarı!)** |
| **RFQ-06** | `S6.8 + S6.1` | Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı (`³He/⁴He` GHS) + `PT420` `4 K` Ön-Soğutucu | `$472k / $779k / $1.338k` | `%16,9` | **#3 Varyans sürücüsü (`%5,3`, en uzun teslim)** |
| **RFQ-07 (`v4.0`)** | `S5.5 + S6.9 + S6.10` | **`v4.0` Paketi:** `S5.5` `808 nm` Flaş-Tavlama Optik Kafası (`Exp130`) + `PT420` Uzak Valf/Körük/OFHC Örgü (`Exp133`) + `M4` `8 nm` `²⁸Si` Epi Kaplama, `3 kΩ` `NbTiN` Veri Yolu & `4 K` `968`-Kapı Çapraz-Anahtar (`Exp131`) | **`$228k / $408k / $760k`** | **`%8,9`** | **#4 Varyans sürücüsü (`%3,4` — `v4.0` kapanış paketi)** |
| **TOPLAM** | **70 Kritik Parça** | **7 Stratejik Tedarik Paketi (`RFQ-01..RFQ-07`)** | **`$1,87M / $3,36M / $6,26M`** | **`%72,9`** | **Toplam BOM MC Varyansının `%92,6`'sı** |

---

## RFQ-01 — İyon Kaynağı, `10→5 keV` Yavaşlatma Kolonu, `HDA-HiRes` Enerji Süzgeci & `PH₃` Gaz Güvenliği (`S1.1, S1.2, S1.3, S1.5, S1.6`)

- **BOM Referansı:** `S1.1-01..05`, `S1.2-01..04`, `S1.3-01..05`, `S1.5-01..03`, `S1.6-01..02` (`19` parça; referans bant `$227,5k / $398,0k / $730,5k` `{Model-Kalibrasyon-Exp114}/{Varsayım}`).
- **Aday Tedarikçi Sınıfı:** Özel iyon-optik/FIB kolon üreticileri (Orsay Physics, Raith, Ionoptika, Specs, Tectra, Hiden/Kimball) + yarı-iletken toksik gaz kabini üreticileri (CS Clean Solutions, Edwards, Entegris, Matheson).

### Teknik Şartname Tablosu (RFQ-01 — `Exp124` Senkronlu)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **İyon Türleri** | `³¹P⁺` (Mod B baz); opsiyonel `²⁹Si⁺`/`²⁸Si⁺` 2. hat (Mod A) | Çift hat ortak çıkış flanşı | Kütle spektrumu (Wien taraması) |
| **Çıkarım & Çarpma Enerjisi (`Exp124`)** | Çıkarım `10–15 keV` → yavaşlatma `5,0–20,0 keV` (wafer `0 V`, üst gömlek `−5 kV`, kaynak `+5 kV`) | `V_extract = 10 keV`, `V_land = 5,000 keV`, toplam kolon `562,66 mm` / `25,92 kg` | HV kalibreli bölücü + retarding analizör |
| **Eksensel Parlaklık (`Exp71/81/124`)** | Süzgeç sonrası net `B ≥ 7,22×10⁴ A/m²/sr` (`1,5 nm` nokta); `Exp124` Liouville akı korunumu kaydı (`39,8k` ham → parlaklık marjı doğrulaması şart) | `B ≥ 1,0×10⁵ A/m²/sr` (süzgeç öncesi `≥ 3,18×10⁵`, `T_i ≤ 0,5 eV`) | Çift-apertür Faraday parlaklık ölçümü |
| **Enerji Yayılımı (`S1.5` `HDA-HiRes`, `Exp124`)** | `ΔE_FWHM ≤ 0,50 eV` (`Arch-B C_c = 2,660 mm` altında `σ_spot ≤ 1,5 nm` için; eski `2,0 eV` sınırı `Exp124`'te sıkılaştı) | **`HDA-HiRes R₀ = 40 mm`, `ΔE_FWHM = 0,453 eV`** (`h = 95 mm, OD = 110 mm`) | Yarı-küresel retarding enerji taraması |
| **Kütle Çözünürlüğü (`S1.2` Wien, `Exp124`)** | `m/Δm ≥ 60` (`²⁸Si / ²⁹Si / ³⁰Si / ³¹P` tam ayrım) | **`B = 0,45 T`, `L = 150 mm`, `OD = 110 mm`**, `m/Δm ≥ 100` | Faraday kütle tarama pik FWHM |
| **Yavaşlatma Optiği (`Arch-B`, `Exp124`)** | `WD = 0,250 mm`, `E_gap ≤ 12 MV/m`, `C_c ≤ 2,70 mm` (`HDA-HiRes` ile eşli) | **`C_c = 2,660 mm`, `E_gap = 10,60 MV/m`**, `σ_spot = 1,428 nm` (`σ_tot = 3,674 nm`) | Simion/COMSOL optik rapor + knife-edge |
| **HV Kararlılığı & Dalgalılık** | `ΔV/V ≤ 1×10⁻⁴` (`±0,5 V @ 5 kV`), dalgalılık `< 50 mVpp` | `≤ 2×10⁻⁵` | HV probu + FFT spektrum |
| **Vakum & Bakeout** | Çıkış flanşı CF100, UHV `≤ 1×10⁻⁹ mbar` (diferansiyel `10⁻⁶ → 10⁻⁹`), `150 °C` bakeout | `≤ 5×10⁻¹⁰ mbar` | RGA + He kaçak `≤ 10⁻¹⁰ mbar·L/s` |
| **`PH₃` Güvenliği (`S1.6`)** | SEMI S2 / NFPA 318 çift-tüplü egzozlu kabin + kuru yıkayıcı; çıkış `< 50 ppb`, `< 5 s` kesme | `< 10 ppb` egzoz | Fabrika gaz sensörü + PLC kilit testi |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** Ar/N₂ yedek gazıyla `10 → 5 keV` geçişte parlaklık, **`ΔE_FWHM ≤ 0,50 eV` (hedef `0,453 eV`, `HDA-HiRes`)** ve `m/Δm ≥ 60` (`0,45 T / 150 mm` Wien) ölçüm sertifikası; `He ≤ 10⁻¹⁰ mbar·L/s` kaçak testi.
- **SAT:** Saha `PH₃` kabini/scrubber + `S7.4` güvenlik PLC entegrasyonu sonrası `³¹P⁺` kararlı 8 saatlik akım sürüklenmesi (`< %1/saat`).
- **Teklif Kırılımı İsteği:** (a) Yalnız tek `³¹P⁺` hattı (`M1` opsiyonu) vs çift hat (`M3`), (b) `S1.2` Wien (`0,45 T, 150 mm`) + `S1.5` `HDA-HiRes` (`R₀=40 mm, ΔE_FWHM ≤ 0,50 eV / 0,453 eV`) bütünleşik vs ayrık modül fiyat/uzunluk kıyaslaması.

---

## RFQ-02 — MEMS Çok-Demet Apertür, Elektrostatik Blanker & `Arch-B` Mini-Lens Dizisi (`S2.1, S2.2, S2.3`)

- **BOM Referansı:** `S2.1-01..04`, `S2.2-01..04`, `S2.3-01..04` (`12` parça; referans bant `$329,5k / $661,0k / $1.387,0k` `{Varsayım}`).
- **Aday Tedarikçi Sınıfı:** Özel MEMS/yüklü-parçacık optiği dökümhaneleri ve araştırma konsorsiyumları (IMS Nanofabrication iş ortağı ekosistemi, Fraunhofer IPMS/ISIT, CEA-Leti, LioniX, VTT, IMT Masken).

### Teknik Şartname Tablosu (RFQ-02 — `Exp124` `Arch-B` Eş-Adımlı `1.024` Dizi Kilidi)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Dizi Ölçeği & Eş-Adım (`Arch-B`, `Exp124`)** | **`32×32 = 1.024` demetcik**, `S2.1`+`S2.2`+`S2.3` tamamı **eş-adımlı `0,50 mm`** (`16,0×16,0 mm` aktif kare, köşegen **`22,63 mm < Ø28,0 mm`** `S1.6`/`S2.1` iç açıklığı → `2,69 mm` radyal marj; `S2.4` `16×` 64-ch karo) | `32×32 = 1.024` demetcik (`0,50 mm` adım; `M2`: `8×8–16×16`) *(tarihsel `32 µm` yalnız `Arch-C` alternatif dipnotudur)* | SEM CD ölçümü + optik haritalama |
| **Apertür Plakası (`S2.1`)** | `30 µm` katkılı SOI Si, `0,50 mm` eş-adımlı `32×32` açıklık (`±50 nm` CD), `Au/Pt` anti-şarj (`<1 Ω/sq`), iç açıklık `Ø28,0 mm` | Eğilme (bow) `≤ 2 µm` (`16,0 mm` aktif alanda) | Beyaz-ışık interferometri + SEM |
| **Blanker Plakası (`S2.2`)** | `0,50 mm` eş-adımlı `1.024` bağımsız elektrostatik saptırıcı (`16×` 64-ch karo); kapı süresi `≤ 1 ms` (`Exp65`), `V_blank ≤ 35 V @ 5 keV` | Kapı süresi `≤ 10 µs`, sızıntı `< 1 nA/kanal` | Prob istasyonu I-V / C-V + dinamik darbe |
| **Yapısal Rezonans (`Exp84`)** | Kalkan plakası ilk öz-frekansı `f₁ ≥ 1,0 MHz` (servo bandından `> 10⁴×` yüksek) | `f₁ ≥ 2,5 MHz` (`Exp84` FEM: `2,59 MHz`) | Lazer Doppler vibrometri (LDV) |
| **Mini-Lens Dizisi (`S2.3` `Arch-B`, `Exp124`)** | 3-yonga hizalı `0,50 mm` eş-adımlı `32×32 = 1.024` elektrostatik yavaşlatıcı yığın (`h = 1,76 mm, OD = 60 mm, WD = 0,250 mm, E_gap = 10,60 MV/m, C_c = 2,660 mm`); `HDA-HiRes` ile **`σ_spot ≤ 1,50 nm`** (`Exp124`: `1,428 nm`) | `σ_spot ≤ 1,35 nm`, delik yuvarlaklığı `±30 nm` | SEM yuvarlaklık + elektron/iyon knife-edge testi |
| **Elektrik Ara-Bağlantı (Interposer)** | UHV uyumlu `LTCC`/`AlN` + TSV/mikro-bump fan-out (`1.024` kanal = `16×` `S2.4` SKY130 64-ch karo ile birebir) | `≥ %98` çalışan demetcik verimi | Süreklilik / kısa-devre otomatik tarama |
| **Vakum & Malzeme** | UHV `≤ 1×10⁻⁹ mbar`, `150 °C` bakeout, ferromanyetik olmayan tutucu | İyon aşındırma (sputter) değişim kaseti | RGA + kinematik tak-çıkar tekrarlanabilirlik `±2 µm` |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** Plaka eğilme haritası (`≤ 2 µm`), rastgele 100 açıklık SEM CD/yuvarlaklık raporu, `1.024` kanallı tam elektrot dizisinde açık/kısa-devre verim haritası (`≥ %98`), `3 kV` lens izolasyon (hi-pot) testi.
- **SAT:** İyon kolonu altında `S9.1-02` knife-edge hedefiyle `σ_spot ≤ 1,50 nm` (`1,428 nm` hedef) ve blanker sönümleme oranı `> 10⁴` doğrulaması.
- **Teklif Kırılımı İsteği:** (a) Tek seferlik NRE/maske bedeli ile birim ek plaka bedelinin (`S9.3-01` yedekler için) ayrıştırılması, (b) `M2` (`8×8 = 64` veya `16×16 = 256` demetcik) vs `M3` (`32×32 = 1.024` demetcik, `0,50 mm` eş-adım) aşamalı fiyatlama.

---

## RFQ-03 — `6-DOF` UHV Piezo Kademe & 3-Eksen Lazer İnterferometri (`S4.3, S4.4`)

- **BOM Referansı:** `S4.3-01..04`, `S4.4-01..04` (`8` parça; referans bant `$100,5k / $163,0k / $282,5k` `{Liste-Çapası}/{Model-Kalibrasyon-Exp114}`).
- **Aday Tedarikçi Sınıfı:** Physik Instrumente (PI PIMars P-562/563 UHV), SmarAct, Attocube (piezo); Renishaw (`XL-80`/`RLE`), Zygo, Attocube IDS (interferometre).

### Teknik Şartname Tablosu (RFQ-03)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Artık Titreşim Payı (`Exp66/79/133`)** | `σ_kademe ≤ 0,50 nm` RMS (`0,5–500 Hz` bantta, kapalı çevrimde; `VC-E` zemin) | `σ_kademe ≤ 0,15 nm` RMS (`Exp133` `CFG4`: `0,1024 nm`) | Kapalı-çevrim interferometre PSD integrali |
| **İnce Piezo Strok & Çözünürlük (`S4.3-01`)** | `6-DOF` (X,Y,Z,θx,θy,θz), XY strok `≥ 200 µm`, Z `≥ 50 µm`, çözünürlük `≤ 0,2 nm` | `300 µm` XY, `0,1 nm` çözünürlük | Kapasitif + interferometre basamak yanıtı |
| **Kaba Adımlama (`S4.3-02`)** | `±25 mm` XY UHV stick-slip/piezo-walk (tüm 50–100 mm yonga kapsama) | `±50 mm` XY, adım tekrarı `≤ 50 nm` | Optik ölçek + interferometre |
| **Lazer İnterferometre (`S4.4`)** | 3-eksen diferansiyel düzlem-ayna (X, Y, Z + opsiyonel θ), çözünürlük `≤ 0,05 nm` (`pm` sınıfı) | `10 pm` çözünürlük, frekans kararlılığı `±0,05 ppm` | Vakumda sabit aynada 1 saat sürüklenme (`< 1 nm/saat`) |
| **Manyetik & UHV Uyumluluk** | Tamamen manyetik olmayan (`Ti`/seramik/Al/Invar), UHV `≤ 1×10⁻⁹ mbar`, `120–150 °C` bakeout | Saçak alan `≤ 50 mT` altında sıfır histerezis | RGA + permeabilite sertifikası (`μ_r < 1,01`) |
| **Gerçek-Zamanlı Arayüz** | `< 5 µs` gecikmeli pozisyon çıkışı (`S4.5-03` atış-anı sapma telafisi & `S6.9-04` FF için) | `< 1 µs` dijital AquadB / EtherCAT / SPI | Osiloskop uçtan-uca gecikme testi |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** Üretici UHV test odasında kapalı-çevrim `σ_kademe ≤ 0,5 nm` RMS raporu, RGA gaz çıkışı sertifikası, lazer frekans kararlılığı kalibrasyon belgesi.
- **SAT:** `S4.1/S4.2` izolasyon masası + `S6.1 PT420` + `RFQ-07B` mekanik ayrıştırma çalışır durumdayken (`1,4 Hz` darbe altında) interferometreyle `σ_kademe ≤ 0,5 nm` (hedef `~0,10 nm`) doğrulaması.
- **Teklif Kırılımı İsteği:** `M1` (2-eksen XY + dar kaba strok) ile `M3` (3-eksen + 6-DOF tam strok) yükseltme farkı; `4 K` kriyo-uyumlu piezo opsiyonu varsa fiyat farkı.

---

## RFQ-04 — `8`-Bobinli `1,50 T` Aktif Karşı-Sargılı Süperiletken Kriyo-Mıknatıs & `Nb (RRR>300)` / `Cryoperm` Kalkan (`S6.3`, `Exp125`)

- **BOM Referansı:** `S6.3-01..05` (`5` parça; referans bant `$106,0k / $185,0k / $340,0k` `{Varsayım}/{Model-Kalibrasyon-Exp114}`).
- **Aday Tedarikçi Sınıfı:** Cryomagnetics, American Magnetics (AMI), Oxford Instruments NanoScience, Cryogenic Ltd., Janis/Lake Shore.

### Teknik Şartname Tablosu (RFQ-04 — `Exp125` & `Exp131` Senkronlu)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Bobin Mimarisi & Geometri (`Exp125`)** | `8`-bobinli aktif karşı-sargılı çift-yarık (`M/S/A/B` üst+alt); iç delik **`Ø150 mm`**, yarık **`36 mm`**, dış çap **`Ø352 mm`** | Yonga düzlemi `z_loc = 0`, `E_mag = 18,9 kJ`, `I/I_c ≤ 0,25` (`Exp125`: `0,212`), `σ_hoop ≤ 60 MPa` (`52,7 MPa`) | 3B CAD/STEP + sarım mekanik FEA |
| **Örnek Alanı & Çift-Kip (`Exp125` + `Exp131`)** | `0,15 – 1,50 T` sürekli ayarlı (**`1,500 T`** ESR/ENDOR kipi + **`B_M4 = 0,1785 T`** `M4` kavite-QED kipi); `r ≤ 2,3 mm` içinde `ΔB/B_0 ≤ 1×10⁻⁴` | **`B_z = 1,500000 T`** (`17,8 ppm`) ve kalıcı **`0,1785 T`** kilit | NMR / 3-eksen Hall prob haritası (`4,2 K`) |
| **Rezonatör Düzlemi Alanı (`Exp109/125`, Risk `R7`)** | Aktif karşı-sargı + `Nb (RRR > 300)` Meissner kabı (`R = 32..34,5 mm`) + `Cryoperm-10` (`R = 39..41 mm`) ile **`B_res ≤ 0,40 T`** | `z = −155 mm` `Ø50 mm` `NbTiN` rezonatör diskinde **`B_res = 22,3 µT`** (`117,1 mT < B_c1 = 135,0 mT` Nb kabuk marjı) | Rezonatör taşıyıcı düzleminde 3-eksen Hall taraması |
| **Sürüklenme (Kalıcı Mod)** | `≤ 0,1 ppm/saat` (ESR/ENDOR `±200 Hz` kararlılık için) | `≤ 0,02 ppm/saat` | 24 saatlik NMR/Hall izleme |
| **Termal Yük (`4 K` Kademe)** | `Bi-2223 HTS` akım uçlarıyla `4 K` statik+dinamik ısı kaçağı `≤ 100 mW` (rampada `≤ 200 mW`) | `≤ 50 mW` kalıcı modda (`Exp125` sistem bütçesi `95 mW` toplam sabit yük dahil) | `PT420` termometri ısı yükü kalibrasyonu |
| **Quench Koruması & Mekanik (`Exp125`)** | Pasif soğuk diyot + boşaltma direnci; adyabatik quench tepe sıcaklığı **`≤ 100 K`**; `S6.8` DR `4 K` flanşına kuru-soğutmalı montaj | **`T_quench = 64,6 K`** (`Exp125`), `1,5 T → 0 T` `< 15 dk` rampa | FAT quench & rampa döngüsü |
| **Eksenel Demet Açıklığı & Saçak Alan** | İyon demetinin yongaya ulaşması için üstten net `Ø150 mm` görüş açıklığı | MEMS lens (`z = +268 mm`) `≤ 110 mT` (`Exp125`: `108,1 mT`), `S1.3-04` mu-metal sınırında `< 5 mT` | Eksenel saçak alan haritası |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** `4,2 K`'da `1,50 T` ve `0,1785 T` (`M4` kipi) tam akım testleri, homojenlik (`≤ 17,8–100 ppm`), `z = −155 mm` `Nb (RRR > 300)` + `Cryoperm-10` kalkanlı `B_res ≤ 0,40 T` (hedef `~22,3 µT`) 3B alan haritası, 12 saat kalıcı mod sürüklenme testi, kontrollü quench testi (`≤ 65–100 K`).
- **SAT:** `S6.8` DR içine montaj sonrası `PT420` `4 K` taban sıcaklığı artışı `< 0,2 K` ve `NbTiN` test rezonatöründe `Q_i ≥ 1×10⁵` korunumu.
- **Teklif Kırılımı İsteği:** Tek-eksen `8`-bobin `1,5 T` karşı-sargılı paket vs `1,5 T` + küçük `±0,1 T` süperiletken trim/vektör bobin opsiyonu; `S6.8` DR üreticisiyle doğrudan mekanik entegrasyon bedeli.

> **Not — `S3.2` IBIC Ön-Uç Elektronikleri (`Exp127` Kilitli `COLD_100K` Profili):** `S3.2` ayrı bir ana RFQ gerektirmez (`%2,9` BOM payı, `%1,2` MC varyansı), ancak özel PCB/COTS tedarikinde **`detector_frontend.net/.cir` varsayılan kilitli `100 K / 1,2 µs / 1 GΩ` şartnamesi** uygulanır: `100 K` soğuk adada `LTC6268` CSA (`C_f = 0,25 pF`, `R_f = 1 GΩ`, `C_S = C_P = 600 pF → τ_s = 1,2 µs`, `Q_ion ~ 342 e⁻ @ 5 keV`, `ENC = 24,1 e⁻`, `η = 0,99936 @ 0,5 pF`, `P_false = 2,59×10⁻⁴`, `204` bileşen / `107` net / `0` ERC).

---

## RFQ-05 — Kriyo-LNA (`≤ 2,8 mW`), Kriyo İzolatör/Koaksiyel & `NbTiN` Çoğullamalı Rezonatör Paketi (`S6.6`) — **`B/C` DUVARI KIRICI**

- **BOM Referansı:** `S6.6-01..07` (`7` parça; referans bant `$409,0k / $765,4k / $1.418,2k` `{Model-Kalibrasyon-Exp114}/{Liste-Çapası}/{Varsayım}`).
- **Kritik Önem (`Exp114/128 v4.0`):** Bu tek paket toplam `v4.0` BOM Monte Carlo varyansının **`%73,4`'ünü** tek başına taşır (`ρ=0,886`; `B`-sınıfı `$12,15k/zincir` vs `C`-sınıfı `$67k–$100k/zincir` farkı `E[C−B] = $4,49M`).
- **Aday Tedarikçi Sınıfı:** Low Noise Factory (LNF, İsveç), Cosmic Microwave Technology (CMT), B&Z Technologies (kriyo-LNA); Low Noise Factory / Quinstar / Raditek / QMC (kriyo izolatör); Delft Circuits, Bluefors, Coax Co., Keycom (kriyo koaksiyel/zayıflatıcı); AMD/Avnet (`ZCU216`); VTT / QuTech / SeeQC / akademik-foundry (`NbTiN` rezonatör).

### Teknik Şartname Tablosu (RFQ-05)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Zincir Sayısı & Çoklama (`Exp112`)** | `56–82` okuma zinciri (`NL = 110–160` rezonatör/hat → `9000` kanal) | `56` zincir (`NL = 160`, `Q_l = 800–1200`) | S21 VNA taraması (`20 mK`) |
| **4 K Kriyo-LNA DC Gücü (`Exp111`)** | `P_DC ≤ 7,8 mW/hat` (`PT420` `2,0 W` ile `56` hatta `0,55 W` kapalı); **`≤ 2,8 mW/hat`** (tek `PT410` için) | `≤ 2,1 mW/hat` (Rebelo 2026 InP HEMT çapası) | `4 K` DC bias + gürültü sıcaklığı ölçümü |
| **4 K Kriyo-LNA Gürültü & Kazanç** | `T_n ≤ 4,0 K`, Kazanç `≥ 30 dB` (okuma bandında: `100–900 MHz` veya yükseltilmiş `4–8 GHz` opsiyonu) | `T_n ≤ 2,0 K`, Kazanç `≥ 38 dB` | Y-faktörü / soğuk-yük gürültü ölçümü (`4 K`) |
| **Ton Gücü & Doğrusallık (`Exp113`)** | Giriş `P_1dB` en az `−55 dBm` (`160` ton @ `−100 dBm/kanal` toplam `−78 dBm` + `>20 dB` tepe-ortalama payı) | `IP3 ≥ −40 dBm`, `NL_max ≥ 316` sıkışmasız | İki-ton intermodülasyon (IMD3) testi |
| **Kriyo İzolatör (`S6.6-02`)** | Ters izolasyon `≥ 20 dB`, ekleme kaybı `≤ 0,5 dB`, manyetik kalkanlı, `20 mK–4 K` uyumlu | Çift-kademe `≥ 35 dB`, `≤ 0,4 dB` kayıp | Kriyo S-parametre (S21/S12) raporu |
| **Koaksiyel Demet (`S6.6-03/04`)** | `56` giriş (`SS304` + `3×` kriyo att., `4 K` yük `≤ 1 mW/hat`) + `56` çıkış (`NbTi/NbTi` `MXC→4 K`, kayıp `<0,1 dB/m`) | Yüksek yoğunluklu esnek stripline / `CryoFlex` opsiyonu | Oda + `4 K` S21 ve termal iletkenlik sertifikası |
| **`NbTiN` Rezonatör Yongaları (`S6.6-07`)** | `Q_i ≥ 1×10⁵ @ ≤0,4 T, 20 mK`, `Q_l = 800–1200`, yerel frekans sapması `σ_f ≤ %0,27`, toplam alan `≤ 10 mm²` (`Exp109/112`) | `Q_i ≥ 2×10⁵`, tasarım aralığı `10–12,5 LW`, kırpma opsiyonu | `20 mK` VNA çentik fiti (`B=0` ve `B=0,4 T`) |
| **RFSoC Sayısallaştırıcı (`S6.6-06`)** | `14` adet `AMD ZCU216` (veya eşdeğeri: `4` hat/kart, `14-bit` ADC/DAC, harici `10 MHz` kilit) | `8` hat/kart yoğunlaştırma opsiyonu (`7` kart) | Çok-tonlu loopback SFDR `> 60 dBc` |

### Kabul Testleri (FAT / SAT) & Teklif Soruları (B/C Duvarı Çözüm Anahtarı)
- **FAT:** Her 56 LNA için `4 K` kazanım/gürültü/DC güç seri-numaralı test raporu; her 56 izolatör için kriyo `S12/S21` raporu; `NbTiN` test kuponunda `B=0,4 T` altında `Q_i ≥ 10⁵` doğrulaması.
- **SAT:** `S6.8` DR içinde 56 zincirin tamamı açıkken `4 K` toplam okuma ısı yükünün `≤ 0,8 W` (`PT420` `%60` pay) ve `MXC` yükünün `≤ 20 µW` ölçülmesi.
- **Kritik Teklif Soruları:**
  1. `100–900 MHz` bandı (SiGe / düşük-frekans InP HEMT) vs `4–8 GHz` bandı (standart InP HEMT + standart kriyo izolatör) için **56 adetlik toplu indirimli birim fiyat** farkı nedir?
  2. `M1` için `2` zincir + `M3` için `56` zincir opsiyonlu kademeli fiyatlandırma (price break @ 2 / 10 / 56 / 100 adet).

---

## RFQ-06 — Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı & `PT420` Ön-Soğutucu (`S6.8 + S6.1`)

- **BOM Referansı:** `S6.8-01..04`, `S6.1-01..03` (`7` parça; referans bant `$471,5k / $778,5k / $1.337,5k` `{Model-Kalibrasyon-Exp114}/{Liste-Çapası}/{Varsayım}`).
- **Karar Bağlamı (`Exp121/128`):** Kullanıcı kararıyla `20 mK` seyreltme ünitesi baz kademedir; `Exp128 v4.0` EVPI analizi tek makine için `20 mK` bazının `1 K` AR-GE'sine üstün olduğunu (`N_be = 6,01` makine) doğrulamıştır.
- **Aday Tedarikçi Sınıfı:** Bluefors (`LD/XLD` sınıfı), Oxford Instruments (`Proteox`), Leiden Cryogenics, FormFactor/Janis (`DR` + `Cryomech PT420`).

### Teknik Şartname Tablosu (RFQ-06)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Taban Sıcaklığı (`MXC`)** | `T_base ≤ 20 mK` (yüksüz), çalışma noktasında `≤ 50 mK` (`Exp116` tek-donor pratiği `~50–100 mK`) | `T_base ≤ 12 mK` | Kalibreli `RuO₂` + gürültü/CMN termometrisi |
| **`MXC` Soğutma Gücü (`Exp110`)** | `≥ 250 µW @ 100 mK` (`56–156` hat yükü `5–19 µW` — `> 10×` marj) | `≥ 400 µW @ 100 mK` | `MXC` kalibreli ısıtıcı yük eğrisi |
| **`4 K` Ön-Soğutma (`S6.1` `PT420`)** | `≥ 1,5 W @ 4,2 K` (`2,0 W` `PT420` sınıfı; `56` hat × `7,8 mW` + mıknatıs + kalkan yükünü tek kafa ile kapatır) | `2,0 W @ 4,2 K` + `55 W @ 45 K`, uzak döner valf (`RFQ-07B` uyumlu) | `4 K` ısıtıcı yük eğrisi |
| **Titreşim İzolasyonu (`S4` & `RFQ-07B`)** | `RFQ-07B` (`S6.9`) uzak döner valf (`500 mm`), `2.000 N/m` CF63 körük ve `4×` OFHC Cu örgü (`52,7 N/m`) ile mekanik arayüzlü | `S4.3` piezo üstünde `σ_stage = 0,1024 nm`, `σ_pointing = 0,1473 nm` (`Exp133`) | `3-eksen` kriyo ivmeölçer / interferometre |
| **RF & UHV Arayüz Kapasitesi** | En az `120` koaksiyel hat (`56` giriş + `56` çıkış + `8` ESR/ENDOR) + `100` DC hattı (`4 K` `968`-kapı çapraz-anahtar kablajı dahil) + **üstten/yandan UHV iyon demeti & yonga transfer portu** | Modüler yan-yükleme / `S5.1` UHV odası arayüzlü kaset | 3B STEP arayüz kontrolü + He kaçak `≤ 10⁻¹⁰ mbar·L/s` |
| **Mıknatıs Entegrasyonu (`RFQ-04`)** | `4 K` flanşında `S6.3` `1,50 T` aktif karşı-sargılı mıknatıs (`~30–60 kg`) mekanik & termal desteği | `RFQ-04` ile ortak anahtar-teslim test | Mekanik FEA + soğuma süresi `< 36 saat` |
| **Gaz İşleme & `³He` Şarjı** | Tam otomatik kuru turbo+scroll `³He/⁴He` GHS, `~20 L STP` yüksek saflıkta `³He` dahil | 7/24 kesintisiz, güç kesintisi otomatik toplama | 72 saat kesintisiz soğuk çalışma (burn-in) |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** Üretici fabrikasında boş ve `1,5 W @ 4 K` + `400 µW @ 100 mK` yapay yük altında `T_MXC ≤ 20 mK` doğrulaması, `36` saat içinde soğuma ve `72` saat kararlı tutma raporu.
- **SAT:** Saha kurulumunda `S6.3` mıknatısı + `S6.6` `56` koaksiyel demet + `S6.9` körük/örgü + `S5.1` UHV arayüzü takılıyken `T_MXC ≤ 25 mK` ve `4 K` sıcaklık `< 4,2 K` doğrulaması.
- **Teklif Kırılımı İsteği:** (a) `³He` izotop gaz fiyatının ayrı kalem olarak opsiyonlanması (güncel spot `$/L STP`), (b) `S6.8` `20 mK` DR ile alternatif kapalı-çevrim `1 K` (`Cryomech PT + 1 K pot`) fiyat & teslim süresi kıyaslaması (`Exp117` referansı için).

---

## RFQ-07 (`v4.0`) — Flaş-Tavlama Optik Kafası (`S5.5`), `PT420` Titreşim Ayrıştırma (`S6.9`) & `M4` Kavite-QED Veri Yolu (`S6.10`)

- **BOM Referansı:** `S5.5-01..04` (`$95k`), `S6.9-01..04` (`$68k`), `S6.10-01..04` (`$245k`) — toplam **`12` parça**, referans bant **`$228,0k / $408,0k / $760,0k`** (`{Varsayım}`; `v4.0` toplam `+$420k` paketinin `S7.1-04` `$12k` COTS BOED GPU düğümü hariç tamamı).
- **Kapanış Dayanağı:** `Exp130` (`EA1–EA6` Risk `R6` flaş-tavlama), `Exp131` (`CM1–CM7` `M4` kavite-QED veri yolu & 2B perkolasyon), `Exp133` (`CY1–CY8` kuple titreşim/FEM/termal ayrıştırma), `Exp134` (`CX1–CX6` fab TCO ve bütçe marjı).
- **Aday Tedarikçi Sınıfı (3 Alt-Lot Olarak Dağıtılır):**
  - **Lot 7A (`S5.5` Flaş-Tavlama):** Coherent/Dilas, Laserline, nLIGHT, Jenoptik (`808 nm` qCW diyot bar + homojenleştirici); MPF/Larson/MDC (`CF63` AR safir pencere); Kleiber/LumaSense (`10 µs` iki-renkli pirometre).
  - **Lot 7B (`S6.9` `PT420` Ayrıştırma):** Bluefors/Cryomech (uzak döner valf + esnek He hattı); Witzenmann/COMVAT/BOA/Senior Metal Bellows (`316L` kenar-kaynaklı CF63 körük); Taiyo/Tekdata/özel kriyo-atölye (`RRR ≥ 200` `4×` OFHC Cu örgü); Newport/Herzan/Speedgoat (`25 dB` harmonik FF DSP).
  - **Lot 7C (`S6.10` `M4` Veri Yolu & `8 nm` `²⁸Si` Epi):** VTT, QuTech/Delft, SeeQC, Lawrence Berkeley / akademik-foundry (`3 kΩ` `NbTiN` `w=100 nm`); Isonics / Air Liquide / Leibniz IKZ / Silicon Quantum Computing iş ortağı (`Δz_cap* = 8±1 nm` düşük-T `²⁸Si` MBE/CVD); SkyWater/Efabless (`4 K` `SKY130` `968`-kapı çapraz-anahtar).

### Teknik Şartname Tablosu (RFQ-07 — `Exp130 / Exp131 / Exp133` Kilitli Parametreleri)

| Alt-Lot & Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **7A (`S5.5-01`) `808 nm` qCW Kaynak & Homojenleştirici (`Exp130`)** | `808 nm` qCW diyot-lazer bar istifi + fiber demetli `84×88×84 mm` düz-tepe kafa; `t_pulse = 0,5–2,0 ms`, `F = 41,15 J/cm² ± %5`, düz-tepe sapma `≤ ±%2`; `T_peak < 1552 K` (erime altı) | **`1,0 ms / 41,15 J/cm²`** → `T_peak = 1440,3 K`, `f_act = %99,98`, `σ_anneal = 0,328 nm`, `T_back = 592,9 K < 700 K`; Mod 1 (`16×16 mm`, `113,1 J / 125,7 kW`) & Mod 2 (`4×4 mm`, `7,85 kW` M1/kompakt) | Darbe enerji ölçer + 2B ışın profil kamerası |
| **7A (`S5.5-02..04`) CF63 Safir, `10 µs` Pirometre & Kilit (`Exp130`)** | `+Y` `Z=500 mm` CF63 safir (`Ø50×8 mm`, temiz açıklık `Ø44 mm`, demet `Ø36 mm`), `T_AR ≥ %97 @ 808 nm`, `LIDT ≥ 100 J/cm² @ 1 ms`; iki-renkli pirometre `900–1700 K` (`≤ 10 µs`); MXC `<1 K` + UHV vana fail-safe mekanik deklanşör (`<5 ms`) | `T_AR = %98,0`, `F_win = 10,56 J/cm²` (`9,47× LIDT`), `±%1,5` kapalı-çevrim enerji integratörü | Spektrofotometre + LIDT sertifikası + PLC kilit testi |
| **7B (`S6.9-01/02`) `PT420` Uzak Valf & CF63 OVC Körük (`Exp133`)** | `500 mm` ofsetli uzak döner valf + `L = 600 mm` esnek He hattı; kenar-kaynaklı `316L` CF63 OVC/UHV körük (`ID = 44 mm`, `OD = 68 mm`, `L_aktif = 120 mm`, `28` boğum, `0,15 mm` sac), **`k_bellows ≤ 6.282 N/m`** | **`k_bellows = 2.000 N/m`** (`3,14×` emniyet), `He ≤ 10⁻¹⁰ mbar·L/s`, `150 °C` bakeout | Kuvvet-deplasman yay testi + He kaçak |
| **7B (`S6.9-03/04`) `4×` OFHC Cu Örgü & `25 dB` FF (`Exp133`)** | DR tarafı `Ø12×397 mm` bara + `4×` paralel S-ilmek OFHC Cu örgü (`2.550 × Ø50 µm` tel/örgü, `L = 100 mm`, `A = 20,03 mm²`, `RRR ≥ 200`), **`k_braid ≤ 60 N/m`**, `ΔT ≤ 5 mK @ 2,5 µW`; `n=1..15` (`1,4–21 Hz`) `25 dB` harmonik FF | **`k_braid = 52,7 N/m`** (`70×` emniyet), `G_hat = 0,675 mW/K` (`ΔT = 3,7 mK`), `PM = 55,2°`, `GM = 8,69 dB`, `σ_stage = 0,1024 nm`, `σ_pointing = 0,1473 nm` (`VC-E`) | Dinamik yay sertliği + `20 mK` termal iletkenlik + kapalı-çevrim PSD |
| **7C (`S6.10-01`) `3 kΩ` `NbTiN` `M4` Veri Yolu (`Exp131`)** | Yüksek-empedanslı `NbTiN` (`t = 9 nm`, `w = 100 nm`, `L_□ = 100 pH/□`), **`Z_r = 3 kΩ`**, `f_r = 5,0 GHz`, `L_res = 300 µm` (`P_node = 10 µm` kıvrımlı hat), `Q_i ≥ 1×10⁵ @ B_M4 = 0,1785 T, 20 mK` | `B_M4 = 0,1785 T` (`< 0,30 T` `%40,5` marj), `F_iSWAP = 0,9655–0,9918` (yük gürültüsü `1,0–0,25 µeV/√Hz`) | `20 mK` VNA `S21` (`B = 0,1785 T`) + SEM genişlik kontrolü |
| **7C (`S6.10-02`) `Δz_cap* = 8±1 nm` `²⁸Si` Epi Kaplama (`Exp131`)** | İmplant sonrası düşük-sıcaklık (`< 450 °C` veya flaş uyumlu) **`Δz_cap* = 8 ± 1 nm`** izotopik `²⁸Si` (`> %99,95`) kaplama; yanal aday aralığı `p_cand = 200 nm` uyumlu; arayüz yük gürültüsü `≤ 1,0 µeV/√Hz` | Hedef `S_ε ≤ 0,25 µeV/√Hz` (flip-flop sweet-spot erişimi `%24,15 → %95,20`, medyan `C = 2.800,1`) | XTEM/ellipsometri kalınlık + SIMS + kriyo yük-gürültü testi |
| **7C (`S6.10-03/04`) `4 K` `968`-Kapı Çapraz-Anahtar & Kapı Elektroniği (`Exp131`)** | `4 K` kademesi `SKY130` çapraz-anahtar çoklama kartı: `L=11` FT yüzey kodu (`N_cand=6`, `%99,40` perkolasyon) için toplam **`968` DC kapı** (`5–8` kapı/düğüm), `4 K` toplam güç `< 50 mW`; düşük-gürültülü (`< 0,5 µV/√Hz`) `20-bit` DC + `5 GHz` kapı kontrolü | `N_cand = 3` (`%100` baz) ve `N_cand = 6` (`%99,40` FT) 2B yüzey kodu anahtarlama; `≤ 0,2 mV` bias kararlılığı | `4 K` fonksiyonel çapraz-anahtar taraması + gürültü spektrumu |

### Kabul Testleri (FAT / SAT) & Teklif Soruları (`RFQ-07`)
- **FAT (Lot 7A/7B/7C):**
  - *7A:* `808 nm / 1,0 ms` `10.000` atışlık kararlılık (`±%1,5`) + ışın düzlüğü (`≤ ±%2`) + `10 µs` pirometre siyah-cisim kalibrasyonu + `100 J/cm²` safir LIDT raporu.
  - *7B:* Körük yay sabiti (`≤ 2.200 N/m`) & `10.000` döngü yorulma + He kaçak (`≤ 10⁻¹⁰ mbar·L/s`); `4×` OFHC Cu örgü yay sabiti (`≤ 60 N/m`) ve `4 K / 20 mK` RRR/iletkenlik sertifikası.
  - *7C:* `3 kΩ` `NbTiN` test kuponunda `B = 0,1785 T, 20 mK` VNA `Q_i` raporu; `8 ± 1 nm` `²⁸Si` kaplama XTEM/SIMS sertifikası; `4 K` `968`-kapı çapraz-anahtar tüm kanal süreklilik/kaçak taraması.
- **SAT:** `S5.1/S6.8` kurulumu sonrası: (1) `S5.5` boş Si kuponda `1440 K` pirometre + `< 5 ms` kilit testi, (2) `PT420` açıkken `VC-E` zeminde `σ_stage ≤ 0,20 nm` & `σ_pointing ≤ 0,25 nm` kapalı-çevrim doğrulaması, (3) `M4` test yongasında `B_M4 = 0,1785 T`'de `5,0 GHz` rezonatör kilidi.
- **Kritik Teklif Soruları (`RFQ-07`):**
  1. *(Lot 7A)* `M1` için kompakt **Mod 2 (`4×4 mm` adım-flaş, `7,85 kW`)** ile `M3` **Mod 1 (`16×16 mm` tek atış, `125,7 kW`)** arasındaki fiyat ve güç kaynağı farkı nedir?
  2. *(Lot 7B)* `S6.9` körük ve `4×` S-ilmek örgü doğrudan `RFQ-06` DR üreticisinin standart fabrika entegrasyonuyla mı yoksa ayrı alt-yükleniciyle mi daha kısa teslim süresine sahiptir?
  3. *(Lot 7C)* `3 kΩ` `NbTiN` (`w = 100 nm`) litografisinde `σ_f` toleransı ve düşük-T `8 ± 1 nm` `²⁸Si` kaplama arayüz yük gürültüsünün (`0,25–1,0 µeV/√Hz`) en küçük NRE lot bedeli nedir?

---

## Teklif Toplama Sonrası Kapanış Protokolü (`Exp128 v4.0` → Fiziksel Tedarik)

1. Yedi RFQ'dan (`RFQ-01..RFQ-07`) gelen bağlayıcı fiyat teklifleri `BOM_DETAILED.csv`'deki `{Model-Kalibrasyon-Exp114}` / `{Varsayım}` hücrelerinin yerine `{Teklif-Çapası}` etiketiyle yazılır (kanonik `BOM.csv` yine değiştirilmez).
2. `experiments/exp128_bom_sensitivity/run_exp128.py` gerçek tekliflerle yeniden koşturulur; özellikle `S6.6` (`RFQ-05`) fiyatının `B` (`~$12k/zincir`) mi yoksa `C` (`>$50k/zincir`) mi geldiği ve `RFQ-07` (`v4.0` `+$408k` kapsamı) sapması kesinleştirilir.
3. Eğer teklif sonrası `Program` tahmini `$50M` yumuşak çizgisini aşarsa (`H140`), aşımın teknik gerekçesi kayıt altına alınır; `$100M` kesin sınırı aşılıyorsa tasarım revizyonu (`NL` artışı / `1 K` alternatif / kanal ölçeği) zorunlu olarak tetiklenir.
