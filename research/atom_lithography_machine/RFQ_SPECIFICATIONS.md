# Atom Litografi Makinesi — Tedarikçi Teklif İstem (RFQ) Teknik Şartnameleri (`RFQ_SPECIFICATIONS.md`)

> **Amaç ve Epistemik Kapsam:** `Exp114` ve `Exp128` (`100.000` örneklemli Monte Carlo) sonuçları, maliyet belirsizliğinin artık fizik modellerinden değil **`B/C` tedarik duvarından** (`$0,59M–$13,07M` kanonik bant; `BOM_DETAILED` toplam varyansının **`%92,8`'i**) kaynaklandığını göstermiştir. Bu belge, içeriden daha fazla varsayım üretmek yerine gerçek tedarikçilerden bağlayıcı fiyat/teslim teklifi toplamak üzere hazırlanmış **6 teknik RFQ paketi** içerir. **Aşağıdaki hedef fiyat bantları gerçek teklif değil, `Exp114/128` `{Model-Kalibrasyon-Exp114}` / `{Liste-Çapası}` / `{Varsayım}` referans bütçeleridir.**

**Tarih:** 2026-11-22  
**Kapsam:** `BOM_DETAILED.csv` içindeki `58` kritik parça — nominal `M3` donanım maliyetinin **`%70,4`'ü (`$2.950.900`)**, Monte Carlo BOM maliyet varyansının **`%92,8`'i**!

| RFQ Kodu | Alt Sistem & BOM Kimlikleri | Paket Kapsamı | `M3` Referans Bant (`P10 / P50 / P90`) | `M3` Nom Payı | MC Varyans Etkisi |
|---|---|---|---:|---:|---|
| **RFQ-01** | `S1.1, S1.2, S1.3, S1.5, S1.6` | Duoplazmatron (`³¹P⁺/²⁹Si⁺`), Wien (`0,45 T, 150 mm`), `Arch-B` `10→5 keV` kolon, `HDA-HiRes` (`R₀=40 mm, 0,453 eV`) & `PH₃` kabin/yıkayıcı | `$228k / $398k / $731k` | `%9,5` | `Exp124` kolon + güvenlik kilidi |
| **RFQ-02** | `S2.1, S2.2, S2.3` | MEMS Apertür, Blanker & `Arch-B` Mini-Lens Dizisi (`0,50 mm` eş-adım, `32×32 = 1.024` demetcik, `16×` karo, `WD=0,250 mm, σ=1,428 nm`) | `$330k / $661k / $1.387k` | `%15,8` | **#2 Varyans sürücüsü (`%5,8`)** |
| **RFQ-03** | `S4.3, S4.4` | `6-DOF` UHV Kaba+İnce Piezo Kademe (`σ≤0,5 nm`) & 3-Eksen Lazer İnterferometre (`pm`) | `$101k / $163k / $283k` | `%3,9` | Konum hata bütçesi çekirdeği |
| **RFQ-04** | `S6.3` | `8`-Bobinli `1,50 T` (`Ø150` bore / `36 mm` yarık / `Ø352` OD, `17,8 ppm`) Kriyo-Mıknatıs & `Nb RRR>300` Kalkan (`22,3 µT`) | `$106k / $185k / $340k` | `%4,4` | Risk `R7` (`Exp125`) donanım kapanışı |
| **RFQ-05** | `S6.6` (`S6.6-01..07`) | `56–82` Zincir `4 K` InP HEMT LNA (`≤2,8 mW`), Kriyo İzolatör/Koaksiyel + `9000`-ch `NbTiN` Rezonatör | `$409k / $765k / $1.418k` | `%18,3` | **#1 Varyans sürücüsü (`%77,3` — `B/C` duvarı!)** |
| **RFQ-06** | `S6.8 + S6.1` | Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı (`³He/⁴He` GHS) + `PT420` `4 K` Ön-Soğutucu | `$472k / $779k / $1.338k` | `%18,6` | **#3 Varyans sürücüsü (`%5,2`, en uzun teslim)** |
| **TOPLAM** | **58 Kritik Parça** | **6 Stratejik Tedarik Paketi** | **`$1,64M / $2,95M / $5,50M`** | **`%70,4`** | **Toplam BOM MC Varyansının `%92,8`'i** |

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
| **Artık Titreşim Payı (`Exp66/79`)** | `σ_kademe ≤ 0,50 nm` RMS (`0,5–500 Hz` bantta, kapalı çevrimde) | `σ_kademe ≤ 0,25 nm` RMS | Kapalı-çevrim interferometre PSD integrali |
| **İnce Piezo Strok & Çözünürlük (`S4.3-01`)** | `6-DOF` (X,Y,Z,θx,θy,θz), XY strok `≥ 200 µm`, Z `≥ 50 µm`, çözünürlük `≤ 0,2 nm` | `300 µm` XY, `0,1 nm` çözünürlük | Kapasitif + interferometre basamak yanıtı |
| **Kaba Adımlama (`S4.3-02`)** | `±25 mm` XY UHV stick-slip/piezo-walk (tüm 50–100 mm yonga kapsama) | `±50 mm` XY, adım tekrarı `≤ 50 nm` | Optik ölçek + interferometre |
| **Lazer İnterferometre (`S4.4`)** | 3-eksen diferansiyel düzlem-ayna (X, Y, Z + opsiyonel θ), çözünürlük `≤ 0,05 nm` (`pm` sınıfı) | `10 pm` çözünürlük, frekans kararlılığı `±0,05 ppm` | Vakumda sabit aynada 1 saat sürüklenme (`< 1 nm/saat`) |
| **Manyetik & UHV Uyumluluk** | Tamamen manyetik olmayan (`Ti`/seramik/Al/Invar), UHV `≤ 1×10⁻⁹ mbar`, `120–150 °C` bakeout | Saçak alan `≤ 50 mT` altında sıfır histerezis | RGA + permeabilite sertifikası (`μ_r < 1,01`) |
| **Gerçek-Zamanlı Arayüz** | `< 5 µs` gecikmeli pozisyon çıkışı (`S4.5-03` atış-anı sapma telafisi için) | `< 1 µs` dijital AquadB / EtherCAT / SPI | Osiloskop uçtan-uca gecikme testi |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** Üretici UHV test odasında kapalı-çevrim `σ_kademe ≤ 0,5 nm` RMS raporu, RGA gaz çıkışı sertifikası, lazer frekans kararlılığı kalibrasyon belgesi.
- **SAT:** `S4.1/S4.2` izolasyon masası + `S6.1 PT420` çalışır durumdayken (`1,4 Hz` darbe altında) interferometreyle `σ_kademe ≤ 0,5 nm` doğrulaması.
- **Teklif Kırılımı İsteği:** `M1` (2-eksen XY + dar kaba strok) ile `M3` (3-eksen + 6-DOF tam strok) yükseltme farkı; `4 K` kriyo-uyumlu piezo opsiyonu varsa fiyat farkı.

---

## RFQ-04 — `8`-Bobinli `1,50 T` Aktif Karşı-Sargılı Süperiletken Kriyo-Mıknatıs & `Nb (RRR>300)` / `Cryoperm` Kalkan (`S6.3`, `Exp125`)

- **BOM Referansı:** `S6.3-01..05` (`5` parça; referans bant `$106,0k / $185,0k / $340,0k` `{Varsayım}/{Model-Kalibrasyon-Exp114}`).
- **Aday Tedarikçi Sınıfı:** Cryomagnetics, American Magnetics (AMI), Oxford Instruments NanoScience, Cryogenic Ltd., Janis/Lake Shore.

### Teknik Şartname Tablosu (RFQ-04 — `Exp125` Senkronlu)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Bobin Mimarisi & Geometri (`Exp125`)** | `8`-bobinli aktif karşı-sargılı çift-yarık (`M/S/A/B` üst+alt); iç delik **`Ø150 mm`**, yarık **`36 mm`**, dış çap **`Ø352 mm`** | Yonga düzlemi `z_loc = 0`, `E_mag = 18,9 kJ`, `I/I_c ≤ 0,25` (`Exp125`: `0,212`), `σ_hoop ≤ 60 MPa` (`52,7 MPa`) | 3B CAD/STEP + sarım mekanik FEA |
| **Örnek Alanı & Homojenlik (`Exp125`)** | `0,30 – 1,50 T` sürekli ayarlı; aktif yonga alanında (`r ≤ 2,3 mm`) `ΔB/B_0 ≤ 1×10⁻⁴` | **`B_z = 1,500000 T`**, homojenlik **`17,8 ppm`** | NMR / 3-eksen Hall prob haritası (`4,2 K`) |
| **Rezonatör Düzlemi Alanı (`Exp109/125`, Risk `R7`)** | Aktif karşı-sargı + `Nb (RRR > 300)` Meissner kabı (`R = 32..34,5 mm`) + `Cryoperm-10` (`R = 39..41 mm`) ile **`B_res ≤ 0,40 T`** | `z = −155 mm` `Ø50 mm` `NbTiN` rezonatör diskinde **`B_res = 22,3 µT`** (`117,1 mT < B_c1 = 135,0 mT` Nb kabuk marjı) | Rezonatör taşıyıcı düzleminde 3-eksen Hall taraması |
| **Sürüklenme (Kalıcı Mod)** | `≤ 0,1 ppm/saat` (ESR/ENDOR `±200 Hz` kararlılık için) | `≤ 0,02 ppm/saat` | 24 saatlik NMR/Hall izleme |
| **Termal Yük (`4 K` Kademe)** | `Bi-2223 HTS` akım uçlarıyla `4 K` statik+dinamik ısı kaçağı `≤ 100 mW` (rampada `≤ 200 mW`) | `≤ 50 mW` kalıcı modda (`Exp125` sistem bütçesi `95 mW` toplam sabit yük dahil) | `PT420` termometri ısı yükü kalibrasyonu |
| **Quench Koruması & Mekanik (`Exp125`)** | Pasif soğuk diyot + boşaltma direnci; adyabatik quench tepe sıcaklığı **`≤ 100 K`**; `S6.8` DR `4 K` flanşına kuru-soğutmalı montaj | **`T_quench = 64,6 K`** (`Exp125`), `1,5 T → 0 T` `< 15 dk` rampa | FAT quench & rampa döngüsü |
| **Eksenel Demet Açıklığı & Saçak Alan** | İyon demetinin yongaya ulaşması için üstten net `Ø150 mm` görüş açıklığı | MEMS lens (`z = +268 mm`) `≤ 110 mT` (`Exp125`: `108,1 mT`), `S1.3-04` mu-metal sınırında `< 5 mT` | Eksenel saçak alan haritası |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** `4,2 K`'da `1,50 T` tam akım testi, aktif alan homojenliği (`≤ 17,8–100 ppm`) ve `z = −155 mm` rezonatör düzleminde `Nb (RRR > 300)` + `Cryoperm-10` kalkanlı `B_res ≤ 0,40 T` (hedef `~22,3 µT`) 3B alan haritası, 12 saat kalıcı mod sürüklenme testi, kontrollü quench testi (`≤ 65–100 K`).
- **SAT:** `S6.8` DR içine montaj sonrası `PT420` `4 K` taban sıcaklığı artışı `< 0,2 K` ve `NbTiN` test rezonatöründe `Q_i ≥ 1×10⁵` korunumu.
- **Teklif Kırılımı İsteği:** Tek-eksen `8`-bobin `1,5 T` karşı-sargılı paket vs `1,5 T` + küçük `±0,1 T` süperiletken trim/vektör bobin opsiyonu; `S6.8` DR üreticisiyle doğrudan mekanik entegrasyon bedeli.

> **Not — `S3.2` IBIC Ön-Uç Elektronikleri (`Exp127` Kilitli `COLD_100K` Profili):** `S3.2` ayrı 7. bir ana RFQ gerektirmez (`%3,1` BOM payı, `%1,2` MC varyansı), ancak özel PCB/COTS tedarikinde **`detector_frontend.net/.cir` varsayılan kilitli `100 K / 1,2 µs / 1 GΩ` şartnamesi** uygulanır: `100 K` soğuk adada `LTC6268` CSA (`C_f = 0,25 pF`, `R_f = 1 GΩ`, `C_S = C_P = 600 pF → τ_s = 1,2 µs`, `Q_ion ~ 342 e⁻ @ 5 keV`, `ENC = 24,1 e⁻`, `η = 0,99936 @ 0,5 pF`, `P_false = 2,59×10⁻⁴`, `204` bileşen / `107` net / `0` ERC).

---

## RFQ-05 — Kriyo-LNA (`≤ 2,8 mW`), Kriyo İzolatör/Koaksiyel & `NbTiN` Çoğullamalı Rezonatör Paketi (`S6.6`) — **`B/C` DUVARI KIRICI**

- **BOM Referansı:** `S6.6-01..07` (`7` parça; referans bant `$409,0k / $765,4k / $1.418,2k` `{Model-Kalibrasyon-Exp114}/{Liste-Çapası}/{Varsayım}`).
- **Kritik Önem (`Exp114/128`):** Bu tek paket toplam BOM Monte Carlo varyansının **`%77,3`'ünü** tek başına taşır (`ρ=0,889`; `B`-sınıfı `$12,15k/zincir` vs `C`-sınıfı `$67k–$100k/zincir` farkı `E[C−B] = $4,48M`).
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
  1. `100–900 MHz` bandı (SiGe / düşük-frekans InP HEMT) vs `4–8 GHz` bandı (standart InP HEMT + standart kriyo izolatör) için **56 adetlik toplu indirimli birim fiyat** farkı nedir? *(Not: `4–8 GHz` katalogda hazır olduğundan `B`-sınıfına çok daha yakın olabilir!)*
  2. `M1` için `2` zincir + `M3` için `56` zincir opsiyonlu kademeli fiyatlandırma (price break @ 2 / 10 / 56 / 100 adet).

---

## RFQ-06 — Kapalı-Çevrim `MXC ~20 mK` Seyreltme Kriyostatı & `PT420` Ön-Soğutucu (`S6.8 + S6.1`)

- **BOM Referansı:** `S6.8-01..04`, `S6.1-01..03` (`7` parça; referans bant `$471,5k / $778,5k / $1.337,5k` `{Model-Kalibrasyon-Exp114}/{Liste-Çapası}/{Varsayım}`).
- **Karar Bağlamı (`Exp121`):** Kullanıcı kararıyla `20 mK` seyreltme ünitesi baz kademedir; `Exp128` EVPI analizi tek makine için `20 mK` bazının `1 K` AR-GE'sine üstün olduğunu doğrulamıştır.
- **Aday Tedarikçi Sınıfı:** Bluefors (`LD/XLD` sınıfı), Oxford Instruments (`Proteox`), Leiden Cryogenics, FormFactor/Janis (`DR` + `Cryomech PT420`).

### Teknik Şartname Tablosu (RFQ-06)

| Parametre | Zorunlu Alt/Üst Sınır (Mandatory) | Hedef Değer (Target) | Doğrulama Yöntemi |
|---|---|---|---|
| **Taban Sıcaklığı (`MXC`)** | `T_base ≤ 20 mK` (yüksüz), çalışma noktasında `≤ 50 mK` (`Exp116` tek-donor pratiği `~50–100 mK`) | `T_base ≤ 12 mK` | Kalibreli `RuO₂` + gürültü/CMN termometrisi |
| **`MXC` Soğutma Gücü (`Exp110`)** | `≥ 250 µW @ 100 mK` (`56–156` hat yükü `5–19 µW` — `> 10×` marj) | `≥ 400 µW @ 100 mK` | `MXC` kalibreli ısıtıcı yük eğrisi |
| **`4 K` Ön-Soğutma (`S6.1` `PT420`)** | `≥ 1,5 W @ 4,2 K` (`2,0 W` `PT420` sınıfı; `56` hat × `7,8 mW` + mıknatıs + kalkan yükünü tek kafa ile kapatır) | `2,0 W @ 4,2 K` + `55 W @ 45 K`, uzak döner valf | `4 K` ısıtıcı yük eğrisi |
| **Titreşim İzolasyonu (`S4` Uyumlu)** | Uzak döner valf + örgülü `OFHC` bağlar; `MXC` plakasında `≤ 50 nm` ham, `S4.3` piezo üstünde `σ ≤ 0,5 nm` uyumlu | `MXC` titreşimi `< 10 nm` RMS (`1–100 Hz`) | `3-eksen` kriyo ivmeölçer / interferometre |
| **RF & UHV Arayüz Kapasitesi** | En az `120` koaksiyel hat (`56` giriş + `56` çıkış + `8` ESR/ENDOR) + `100` DC hattı + **üstten/yandan UHV iyon demeti & yonga transfer portu** | Modüler yan-yükleme / `S5.1` UHV odası arayüzlü kaset | 3B STEP arayüz kontrolü + He kaçak `≤ 10⁻¹⁰ mbar·L/s` |
| **Mıknatıs Entegrasyonu (`RFQ-04`)** | `4 K` flanşında `S6.3` `1,50 T` aktif karşı-sargılı mıknatıs (`~30–60 kg`) mekanik & termal desteği | `RFQ-04` ile ortak anahtar-teslim test | Mekanik FEA + soğuma süresi `< 36 saat` |
| **Gaz İşleme & `³He` Şarjı** | Tam otomatik kuru turbo+scroll `³He/⁴He` GHS, `~20 L STP` yüksek saflıkta `³He` dahil | 7/24 kesintisiz, güç kesintisi otomatik toplama | 72 saat kesintisiz soğuk çalışma (burn-in) |

### Kabul Testleri (FAT / SAT) & Teklif Soruları
- **FAT:** Üretici fabrikasında boş ve `1,5 W @ 4 K` + `400 µW @ 100 mK` yapay yük altında `T_MXC ≤ 20 mK` doğrulaması, `36` saat içinde soğuma ve `72` saat kararlı tutma raporu.
- **SAT:** Saha kurulumunda `S6.3` mıknatısı + `S6.6` `56` koaksiyel demet + `S5.1` UHV arayüzü takılıyken `T_MXC ≤ 25 mK` ve `4 K` sıcaklık `< 4,2 K` doğrulaması.
- **Teklif Kırılımı İsteği:** (a) `³He` izotop gaz fiyatının ayrı kalem olarak opsiyonlanması (güncel spot `$/L STP`), (b) `S6.8` `20 mK` DR ile alternatif kapalı-çevrim `1 K` (`Cryomech PT + 1 K pot`) fiyat & teslim süresi kıyaslaması (`Exp117` referansı için).

---

## Teklif Toplama Sonrası Kapanış Protokolü (`Exp128` → `Exp129+`)

1. Altı RFQ'dan gelen bağlayıcı fiyat teklifleri `BOM_DETAILED.csv`'deki `{Model-Kalibrasyon-Exp114}` / `{Varsayım}` hücrelerinin yerine `{Teklif-Çapası}` etiketiyle yazılır (kanonik `BOM.csv` yine değiştirilmez veya ayrı karar kaydıyla güncellenir).
2. `experiments/exp128_bom_sensitivity/run_exp128.py` gerçek tekliflerle yeniden koşturulur; özellikle `S6.6` (`RFQ-05`) fiyatının `B` (`~$12k/zincir`) mi yoksa `C` (`>$50k/zincir`) mi geldiği kesinleşir ve `P(Program > $50M)` / `P(Program > $100M)` olasılıkları daraltılır.
3. Eğer teklif sonrası `Program` tahmini `$50M` yumuşak çizgisini aşarsa (`H140`), aşımın teknik gerekçesi masaüstü `BUTCE_DURUMU.md` dosyasına yazılır; `$100M` kesin sınırı aşılıyorsa tasarım revizyonu (`NL` artışı / `1 K` alternatif / kanal ölçeği) zorunlu olarak tetiklenir.
