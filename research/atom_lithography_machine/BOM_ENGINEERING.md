# Atom Litografi Makinesi — Parça-Düzeyi Mühendislik BOM Analizi (`BOM_ENGINEERING.md`)

> **Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Bu belge, kanonik 40 satırlık `BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` — değiştirilmemiştir) dosyasının `BOM_DETAILED.csv` altında **145 fiziksel parça/alt-montaj satırına** açılmış mühendislik çözümlemesidir. **Hiçbir satır gerçek tedarikçi fiyat teklifi değildir.** Tüm USD değerleri `M3` Altın Ölçek (`NL=163`, `56` okuma zinciri, `Arch-B` eş-adımlı `0,50 mm` / `32×32 = 1.024` demetcik [`16×` 64-ch karo], `s=0,5` zarf, `S6.8=20 mK` seyreltme baz kademesi) için satır-genişletilmiş toplamlar olup `{Liste-Çapası}` (`%10,0`), `{Model-Kalibrasyon-Exp114}` (`%58,0`), `{Varsayım}` (`%32,0`) veya `{Program-NRE-Kapsam}` (`S8` yazılım, `$0` donanım alımı) etiketlidir.

**Tarih:** 2026-11-22 *(Exp124/125/127 kesin fizik senkronu)*  
**Dayanak:** `BOM.csv` (`Exp121/122` kanonik baz), `BOM_DETAILED.csv` (`145` parça), `Exp85–Exp122` maliyet zinciri, `Exp124` (`10→5 keV` `Arch-B` yavaşlatma `WD=0,250 mm, C_c=2,660 mm, E_gap=10,60 MV/m` + `HDA-HiRes R₀=40 mm, ΔE_FWHM=0,453 eV` + Wien `0,45 T, 150 mm`), `Exp125` (`8`-bobinli `Ø150 mm` bore / `36 mm` yarık / `Ø352 mm` OD `1,500000 T ±17,8 ppm` kriyo-mıknatıs + `Nb RRR>300` Meissner kalkan `22,3 µT` / `64,6 K` quench), `Exp127` (`100 K` soğuk adada `LTC6268` CSA `1,2 µs / 1 GΩ, ENC=24,1 e⁻, η=0,99936 @ 5 keV`), `Exp128` (`100.000` örneklemli korelasyonlu Monte Carlo).

---

## 1. Yönetici Özeti ve `BOM.csv` / `Exp122` → `BOM_DETAILED.csv` Uzlaştırması

Kanonik `BOM.csv` (`40` satır) büyüklük-mertebesi sınıf modeliyle (`Exp114` medyan `$720/birim`) `M3` altın ölçekte **`$2.531.244`** (`3.515,62` sınıf-birimi; aralık `$0,595M–$13,073M`) verir. Parça düzeyinde `BOM_DETAILED.csv` (`145` parça; kanonik `40/40` satırın tamamı + `S1.5` enerji süzgeci & `S1.6` `PH₃` gaz güvenliği açık ek satırları) ise **`$4.189.600`** nominal (`$2.329.000` P10 alt – `$7.834.700` P90 üst) donanım toplamına ulaşır.

### 1.1 Alt-Sistem Bazlı Tam Uzlaştırma Tablosu (`Exp122` vs `M1` vs `M3`)

| Alt Sistem | Parça Sayısı | `Exp122` Kanonik (`@$720/u`) | `M1` Tek-Demet Prototip (Nom `[P10–P90]`) | `M3` `BOM_DETAILED` (Nom `[P10–P90]`) | `M3 − Exp122` Farkı (`Δ`) | Farkın Kök Mühendislik Nedeni |
|---|---:|---:|---:|---:|---:|---|
| **S1** Kaynak & Kolon | 22 | `$237.600` | `$319.750` `[$183k–$585k]` | `$416.000` `[$238k–$763k]` | **`+$178.400`** | `Exp124` `Arch-B` `10→5 keV` yavaşlatma lensi (`WD=0,250 mm, C_c=2,660 mm`, `+$28k`) + `HDA-HiRes` enerji süzgeci (`R₀=40 mm, ΔE_FWHM=0,453 eV`, `S1.5`, `$62k`) + Wien (`0,45 T, 150 mm`) + gerçek `PH₃` gaz kabini/yıkayıcı (`S1.6`, `$58k`) vs `Exp83` `ADDERS=+20u ($14,4k)` |
| **S2** MEMS Çok-Demet Kafa | 18 | `$10.633` | `$147.750` `[$80k–$289k]` | `$775.500` `[$392k–$1.606k]` | **`+$764.867`** | **En büyük yapısal açık:** `Exp122` `(nb/10⁶)^0,7` ölçeklemesi `nb=100`'de `S2.1–2.3` (`3000u` `D` geliştirme) sabit maske/DRIE/TSV/wafer-bonding NRE'sini `$3,4k`'ya ezdi; `BOM_DETAILED` gerçek MEMS fab/NRE'yi (`$370k` NRE + `$291k` plakalar/`Arch-B` lens/interposer + `$115k` SKY130/metroloji) açar |
| **S3** IBIC Algılama | 14 | `$146.081` | `$88.550` `[$48k–$168k]` | `$224.000` `[$120k–$429k]` | **`+$77.919`** | `Exp127` kilitli `100 K` soğuk-ada (`COLD_100K`) `16×8` `LTC6268` CSA (`1,2 µs / 1 GΩ, Q_ion~342 e⁻, ENC=24,1 e⁻, η=0,99936 @ 5 keV`) + kanal-başı trim DAC + `<5 cm` mikro-koaksiyel + 4× CF63 (`+$65,1k` net delta) |
| **S4** Konum & Titreşim | 17 | `$241.200` | `$233.920` `[$142k–$411k]` | `$253.000` `[$153k–$446k]` | **`+$11.800`** | `Exp122` ile `%4,9` içinde birebir uyum (`Renishaw XL-80` + `PI PIMars` UHV piezo + aktif tabla + Invar çerçeve) |
| **S5** Vakum & Süreç | 16 | `$163.800` | `$196.800` `[$113k–$358k]` | `$243.000` `[$138k–$444k]` | **`+$79.200`** | `S5.2` pompa seti `Exp114` gerçek çapası (`$16k` + kuru scroll + RGA = `$28k`) vs `s³` ölçekli `$1,8k` (`2,5u`); gerçek CF100 load-lock + VAT vana + manyetik transfer |
| **S6** Kriyo, DR, Mıknatıs & Okuma | 30 | `$1.578.650` | `$1.056.300` `[$628k–$1.855k]` | `$1.925.900` `[$1.095k–$3.473k]` | **`+$347.250`** | `S6.6` 56-zincir faturası (**`$680.400`**) ve `S6.8` 20 mK DR (**`$720.000`**) `Exp114/122` ile **kuruşu kuruşuna eşit**; fark: `Exp125` `1,5 T / ≤0,4 T` aktif karşı-sargılı mıknatıs + Nb kalkan (`$185k` vs `s³` `$9k` = `+$176k`), NbTiN 9000-rezonatör çip/paket (`+$85k`), yeni `PT420` (`$58,5k` vs 2. el `PT410` `$21,6k`) |
| **S7** Kontrol & Hesaplama | 13 | `$153.281` | `$104.450` `[$60k–$192k]` | `$204.200` `[$115k–$378k]` | **`+$50.919`** | `2× Lambda Vector` GPU (`$21,2k` çapa), `PXIe` AWG şase, `4 K` SKY130 kılıflama/tarama, 2× `42U` EMI kabin & SIL-2 güvenlik PLC |
| **S8** Yazılım & RTL | 8 | `$0` | `$0` | `$0` | **`$0`** | Proje-içi yazılım/RTL (`machine_control`, `CellISA`, `blanker_tile`, GRAPE/XY8); mühendislik işçiliği Program `×3–×10` NRE içindedir (çifte sayım yok) |
| **S9** Sarf & Yedekler | 7 | `$0` | `$42.250` `[$22k–$82k]` | `$148.000` `[$78k–$297k]` | **`+$148.000`** | `BOM.csv`'de sınıfsız (`0u`) bırakılan kalibrasyon yongaları (`$35k`), 1 yıllık `PH₃/²⁹SiF₄`/katot sarfı (`$18k`), yedek MEMS plakaları + 4 yedek kriyo-LNA zinciri + kriyostat bakım kiti (`$95k`) |
| **TOPLAM** | **145** | **`$2.531.244`** | **`$2.189.770`** `[$1,28M–$3,94M]` | **`$4.189.600`** `[$2,33M–$7,83M]` | **`+$1.658.356`** | **Uzlaştırma aritmetik hatası: `$0,00` (`< 10⁻⁶`)** |

### 1.2 Kurumsal Delta Köprüsü (`Exp122` `$2,531M` → `BOM_DETAILED` `$4,190M`)

| Köprü Adımı | Tutar (USD) | Toplam Artıştaki Pay | Açıklama |
|---|---:|---:|---|
| **`Exp122` Merkez Bazı (`3.515,62u @ $720`)** | `$2.531.244` | — | `40` satır, `S6.8=D (20 mK)`, `NL=163`, merkez zincir `16,875` |
| `+ S2` MEMS Sabit Maske / DRIE / TSV / Bonding NRE | `+$764.867` | `%46,1` | `Exp122` üssel ölçeğinin bastırdığı sabit MEMS geliştirme donanımı |
| `+ COTS / UHV / PT420 / EMI` Gerçek Çapa Uyumu | `+$285.769` | `%17,2` | Yeni `PT420`, `S5.2` pompa çapası, UHV vana/transfer, `S7` EMI/PLC |
| `+ Exp125` `1,5 T / ≤0,4 T` Mıknatıs + Nb Kalkan + NbTiN | `+$261.000` | `%15,7` | Aktif karşı-sargılı bobin + Nb/Cryoperm kalkan (`+$176k`) + 9000 NbTiN çip (`+$85k`) |
| `+ S9` Kalibrasyon Yongaları, Gaz & Yedek MEMS/LNA | `+$148.000` | `%8,9` | `BOM.csv`'de sınıfsız olan operasyonel donanım |
| `+ Exp124` `10→5 keV` Yavaşlatma + `HDA-HiRes` (`ΔE_FWHM ≤ 0,50 eV`, `0,453 eV`) + `PH₃` | `+$133.600` | `%8,1` | `Exp83` `ADDERS=+20u ($14,4k)` üzerine gerçek `HDA-HiRes` UHV süzgeç + scrubber + `Arch-B` lens |
| `+ Exp127` Kilitli `100 K` `16×8` Düşük-C `LTC6268` IBIC Ön-Uç | `+$65.119` | `%3,9` | `100 K / 1,2 µs / 1 GΩ` (`342 e⁻, η=0,99936`) CSA + kanal-başı trim DAC + `<5 cm` mikro-koaksiyel |
| **`= M3 BOM_DETAILED` Nominal Donanım Toplamı** | **`$4.189.600`** | **`%100,0`** | **`$50M` yumuşak bütçe çizgisinin `11,9×`, `$100M` sert sınırın `23,9×` altında** |

---

## 2. Malzeme, Vakum, Kriyojenik ve Manyetik Uyumluluk Matrisi

Atom litografi makinesi aynı fiziksel zarf içinde dört aşırı fiziksel rejimi birleştirir: **UHV (`≤ 10⁻⁹ mbar`, `150 °C` bakeout)**, **kriyojenik 5 kademe (`300 K → 50 K → 4 K → Still 0,8 K → CP 100 mK → MXC 20 mK`)**, **yüksek/sıfır manyetik alan geçişi (`1,50 T` örnek ↔ `≤ 0,25–0,40 T` rezonatör düzlemi ↔ `< 1 µT` iyon kolonu)** ve **toksik/piroforik `PH₃` gazı**.

| Bölge / Sıcaklık Kademesi | Kapsanan Parçalar (`BOM_DETAILED`) | Vakum / Basınç Rejimi | Onaylı Yapısal & İletken Malzemeler | Yasaklı / Riskli Malzemeler & Kritik Kısıtlar |
|---|---|---|---|---|
| **Kaynak & `PH₃` Hattı (`300 K`, su soğutmalı)** | `S1.1`, `S1.2`, `S1.6`, `S9.2` | Kaynak `10⁻⁶ mbar` → diferansiyel `10⁻⁹ mbar`; egzoz negatif basınç | `316L VAR` (elektro-parlatılmış), Molibden anot, `Al₂O₃`, metal VCR contalar | Pirinç/elastomer `PH₃` hattında **yasak**; sızıntı `≤ 10⁻¹⁰ mbar·L/s`; `50 ppb` PLC acil kapama (`S7.4-04`) |
| **İyon Kolonu & MEMS Kafa (`300 K`, UHV)** | `S1.3–1.5`, `S2.1–2.5`, `S5.1–5.3` | UHV `≤ 10⁻⁹ mbar`, `150 °C` bakeout | `316LN` (manyetik olmayan), `Ti-6Al-4V`, katkılı Si (SOI), `Au/Pt` anti-şarj, Safir, `AlN`, `LTCC`, `Kapton` | Ferromanyetik çelik (kolonda demet sapması yapar), yüksek gaz çıkışlı epoksi/PVC/çinko **yasak**; kafa `f₁ ≥ 2,59 MHz` (`Exp84`) |
| **Konum & Metroloji (`300 K`, UHV + Atmosfer)** | `S4.1–4.5` | Kademe/ayna UHV `10⁻⁹ mbar`; granit/aktif tabla atmosfer | Siyah diyabaz granit, `Invar-36` (`CTE ≤ 1,2 ppm/K`), `Zerodur/ULE` (`<0,02 ppm/K`), manyetik olmayan `Ti` piezo flekstür | Manyetik paslanmaz (304 soğuk çekim) piezo kademede **yasak** (`S6.3` saçak alanıyla kuvvet/histerezis üretir) |
| **Vakum-İçi IBIC Ön-Uç (`100 K` Soğuk Ada, UHV)** | `S3.1–3.2` (`Exp127`) | UHV `10⁻⁹ mbar` | Yüksek-direnç Si (`>10 kΩ·cm`), Safir/AlN, manyetik-olmayan `BeCu+Au`, `Rogers 4350B`/`Al₂O₃` PCB, kilitli `COLD_100K` `LTC6268` CSA (`1,2 µs / 1 GΩ, Q_ion~342 e⁻, ENC=24,1 e⁻, η=0,99936 @ 5 keV`), `PTFE` mikro-koaksiyel | Standart FR4 vakum içinde **yasak** (gaz çıkışı); kablo boyu `< 5 cm` zorunlu (`C_par < 0,15 pF` → `C_tot ≤ 0,5 pF`, `Exp72/127`) |
| **Kriyo Kalkan & `4 K` Kademe (`50 K / 4 K`)** | `S6.1–6.5`, `S6.6-01/02`, `S7.3` | Kriyo-vakum `≤ 10⁻⁷ mbar` | Tavlanmış `OFHC Cu` (`RRR > 200`, altın kaplı), `Al 6061` (`50 K`), `8`-bobin `NbTi/Cu` (`Ø150` bore / `36 mm` yarık / `Ø352` OD, `64,6 K` quench), `Bi-2223 HTS` akım uçları, `SS304`/`CuNi` koaksiyel | Bakır dışı düşük-RRR alaşım termal yolda **yasak**; `4 K` okuma yükü `≤ 1,0 W` (`PT410`) veya `≤ 1,5 W` (`PT420`, `%25` pay) |
| **Manyetik Geçiş & `MXC 20 mK` Ölçüm Adası** | `S6.3-02/03`, `S6.6-04/07`, `S6.7`, `S6.8` | UHV / Kriyo-vakum (`20 mK`) | Yüksek saflıkta `Nb` (`RRR > 300, Tc=9,2 K`), `Cryoperm-10`, `NbTiN` (`Lk=50 pH/sq`), süperiletken `NbTi/NbTi` koaksiyel, `Ag`-sinter ısı eşanjörü, `Eccosorb CR-124` | Nikel kaplı SMA konnektör `MXC`'de **yasak** (manyetik gürültü ve `NbTiN` akı yakalama); rezonatör düzleminde (`z = −155 mm`) kalkanlı `B_res = 22,3 µT` (`≪ 0,40 T` sınırı; `Exp109/125`) |

---

## 3. Tedarik Sınıfı (`COTS / CUS / R&D`) ve Tedarik Zinciri Risk Haritası

### 3.1 `BOM_DETAILED.csv` Tedarik ve Epistemik Dağılımı

| Tedarik Sınıfı | Parça Sayısı | `M3` Alt (`P10`) | `M3` Nominal (`P50`) | `M3` Üst (`P90`) | `M3` Nominal Payı | Tipik Teslim Süresi (Varsayım) |
|---|---:|---:|---:|---:|---:|---|
| **`COTS`** (Rafta/Katalog) | 64 | `$1.016.200` | `$1.724.200` | `$3.040.200` | **`%41,2`** | 4–24 hafta *(DR `S6.8`: 26–44 hafta)* |
| **`CUS`** (Özel Üretim, Bilinen Teknoloji) | 51 | `$638.800` | `$1.159.400` | `$2.156.500` | **`%27,7`** | 12–36 hafta |
| **`R&D`** (Gösterimsiz / AR-GE Gerekli) | 11 | `$512.000` | `$1.020.000` | `$2.112.000` | **`%24,3`** | 6–24 ay *(iteratif)* |
| **`COTS/CUS`** (Katalog Uyarlama) | 9 | `$124.000` | `$214.000` | `$381.000` | `%5,1` | 8–20 hafta |
| **`CUS/R&D`** (Özel + AR-GE Sınırı) | 2 | `$38.000` | `$72.000` | `$145.000` | `%1,7` | 16–36 hafta |
| **`IN-HOUSE`** (`S8` Yazılım/RTL) | 8 | `$0` | `$0` | `$0` | `%0,0` *(HW)* | Proje içi geliştirme (`Program NRE`) |
| **TOPLAM** | **145** | **`$2.329.000`** | **`$4.189.600`** | **`$7.834.700`** | **`%100,0`** | — |

- **Epistemik Dağılım (`M3` Nominal):** `{Liste-Çapası}`: `15` parça (`$417.400`, `%10,0`) | `{Model-Kalibrasyon-Exp114}`: `93` parça (`$2.429.700`, `%58,0`) | `{Varsayım}`: `29` parça (`$1.342.500`, `%32,0`) | `{Program-NRE-Kapsam}`: `8` parça (`$0`).

### 3.2 Kritik Tedarik Risk Matrisi & Azaltım Stratejileri

| Öncelik | Risk Kalemi (`BOM_DETAILED`) | Maliyet Varyansı / Etkisi (`Exp128`) | Tek-Kaynak / Darboğaz Riski | Somut Azaltım Eylemi |
|---|---|---|---|---|
| **P0 (KRİTİK)** | **`S6.6-01/02` 56× Kriyo-LNA (`≤2,8 mW`) + İzolatör (`B/C` Duvarı)** | **BOM varyansının `%77,3`'ü** (`ρ=0,889`, P10–P90 salınımı `$8,87M`) | `100–900 MHz` bandında `≤2,1 mW` InP HEMT katalog parçası değil (Rebelo 2026 `4–8 GHz` ekstrapolasyonu); LNF/QMC teklif usulü | **RFQ-05'i hemen gönder;** 100–900 MHz SiGe (`1,8 mW`) veya `4–8 GHz` yükseltilmiş okuma bandı + `PT420` (`7,8 mW` LNA ile `0,55 W @ 56` hat zaten kapanıyor!) alternatifini teklifte sor |
| **P1 (YÜKSEK)** | **`S2.1–S2.3` MEMS Apertür / Blanker / `Arch-B` Mini-Lens NRE** | Varyansın `%5,8`'i (`$661k` nom, `$1,39M` P90) | 3-yonga hizalı `Arch-B` (`0,50 mm` eş-adımlı `32×32 = 1.024` demetcik, `WD=0,250 mm, σ_spot=1,428 nm`) + TSV dünyada sayılı MEMS dökümhanelerinde yapılır | **RFQ-02 ile aşamalı M1→M2→M3:** M1'de MEMS dizisi beklemeden tek-delik/FIB ile başla (`S2` `$148k`), M2'de `8×8–16×16` prototip, M3'te `32×32 = 1.024` (`16×` karo) |
| **P1 (YÜKSEK)** | **`S6.8` `20 mK` Seyreltme Kriyostatı + `³He` İzotop Şarjı** | Varyansın `%5,2`'si (`$720k` nom, `$1,25M` P90) | 26–44 hafta teslim süresi (Bluefors / Oxford / Leiden); `³He` gaz piyasası jeopolitik olarak oynak | **RFQ-06'yı M1 fazı başında erken siparişle kilitle** (M1 ve M3'te ortak sabit demirbaş); `1 K` AR-GE'sini filo (`N ≥ 6`) ölçeğine ertele (`Exp128 CU5`) |
| **P2 (ORTA-YÜKSEK)** | **`S6.3` `1,50 T / ≤0,4 T` Aktif Karşı-Sargılı Mıknatıs (`Exp125`)** | `$185k` nom (`$106k–$340k`) | Özel `NbTi` karşı-sargı + `Nb/Cryoperm` kalkan entegrasyonu, quench ve `DR` mekanik birleşimi | **RFQ-04 ile DR üreticisi (RFQ-06) ortak mekanik/termal arayüz kontrolü (ICD)** yap |
| **P2 (ORTA)** | **`S5.4-01` İzotopik `²⁸Si/²⁹Si (f=%1)` Epitaksiyel Yonga** | `$56k` nom (`$30k–$105k`) | `²⁸SiH₄` gaz arzı sınırlı (dünyada 2–3 tedarikçi); 4–9 ay bekleme | M1'de küçük 5-yonga deneme lotu (`$16,8k`) ile erken sipariş + SIMS doğrulaması |
| **P2 (ORTA)** | **`S2.4/S7.3` SKY130 Anten-Temiz Tape-Out (`R5` / `Exp123`)** | `$126k` nom (S2.4+S7.3 ASIC) | Güncel OpenROAD + OpenRCX olmadan bant çıkışı kilitli (`Exp123`) | M1 prototipinde blanker kontrolünü FPGA (`S3.3`) + harici HV sürücüyle yürüt; SKY130 tape-out'u M2'ye hizala |

---

## 4. Aşamalı Maliyet Kırılımı: `M1` Tek-Demet Laboratuvar Prototipi vs. `M3` Altın Ölçek

`DESIGN.md` §10 yol haritasına göre ilk fiziksel gösterim **M1** (tek-demet sayılmış implantasyon + tek-yuva ölç-seç-kalibre döngüsü) olup, çok-demetli MEMS dizisi (`M2`) ve `9000`-kanallı altın ölçek (`M3`) sonradan eklenir. `Exp128` parça-bazlı indirgeme modeli (`run_exp128.py`) iki aşama arasındaki gerçek finansal geçişi nicelleştirir:

| Boyut / Alt Sistem | `M1` Tek-Demet Prototipi | `M3` Altın Ölçek (`BOM_DETAILED`) | `M1 / M3` Oranı | `M1 → M3` Temel Fark |
|---|---:|---:|---:|---|
| **Demetcik / Okuma Kanalı** | `1` demetcik / `2` okuma zinciri | `32×32 = 1.024` demetcik (`0,50 mm` `Arch-B`, `16×` karo) / `56` zincir (`9000` kanal) | — | Paralelleştirme adımı |
| **`S1` Kaynak & Kolon** | `$319.750` | `$416.000` | `%76,9` | Yalnız `³¹P⁺` hattı (`²⁹Si⁺` Mod A yok), tek Wien/Faraday; `HDA-HiRes` (`ΔE_FWHM ≤ 0,50 eV`, `0,453 eV`) + `PH₃` kabini + `10→5 keV` kolon tam korunur |
| **`S2` Kafa / Odak** | `$147.750` | `$775.500` | `%19,1` | Çok-demet MEMS NRE/TSV yok; tek-delikli FIB/pinhole + tek-eksen Einzel lens + tek-kanal blanker |
| **`S3` IBIC Algılama** | `$88.550` | `$224.000` | `%39,5` | `16×8` yerine `1–2×8` kanallı vakum-içi IBIC modülü + tek CF63 geçiş + tek FPGA |
| **`S4` Konum & İnterferometri** | `$233.920` | `$253.000` | `%92,5` | `σ ≤ 0,5 nm` piezo + aktif izolasyon + 2-eksen interferometri M1'de de neredeyse tam gerekir |
| **`S5` UHV & Süreç** | `$196.800` | `$243.000` | `%81,0` | UHV oda/pompa/tavlama sabit; izotopik epi lotu `25 → 5` yongaya iner |
| **`S6` Kriyo, DR, Mıknatıs & Okuma** | `$1.056.300` | `$1.925.900` | `%54,8` | **`20 mK` DR (`$720k`) + `PT420` + `1,5 T` mıknatıs M1'de de sabit tabandır;** okuma `56 → 2` zincire ve `14 → 1` `ZCU216`'ya iner (`−$656k`) |
| **`S7` Kontrol & Hesaplama** | `$104.450` | `$204.200` | `%51,2` | 1× GPU iş istasyonu, 1× AWG, 1× EMI kabin; SKY130 MPW M2'ye ötelenir |
| **`S9` Sarf & Yedekler** | `$42.250` | `$148.000` | `%28,5` | Çok-demet MEMS yedekleri yok; yarı kalibrasyon/gaz kiti |
| **TOPLAM DONANIM (`P50 [P10–P90]`)** | **`$2.189.770`** `[$1,28M–$3,94M]` | **`$4.189.600`** `[$2,33M–$7,83M]` | **`%52,3`** | **M1 donanımının `%82`'si M3'e doğrudan taşınabilir demirbaştır!** |
| **Tahmini Program (`×3` – `×5,5` – `×10`)** | `$6,6M` – `$12,0M` – `$21,9M` | `$12,6M` – `$23,0M` *(MC P50 `$28,2M`)* – `$41,9M` *(MC P50 `$50,1M`)* | — | M1 programı en sert `×10` varsayımında bile `$50M` çizgisinin yarısının altındadır |

**Kritik Mimari Ders:** `M1` prototipinin donanım bedelinin (`$2,19M`) yaklaşık **`$1,80M`'si** (`20 mK` DR, `PT420`, `1,5 T` mıknatıs, UHV oda/pompalar, `PH₃` gaz güvenliği, `6-DOF` piezo, interferometre, `HDA-HiRes` `ΔE_FWHM ≤ 0,50 eV` [`0,453 eV`] enerji süzgeci) `M3` makinesinin doğrudan çekirdek gövdesidir — yani `M1` harcaması çöpe gitmez, `M2/M3`'e modüler (`MODULAR.md`) yükseltilebilir bir çekirdek platform kurar.

---

## 5. Çapraz Referanslar

- Parça listesi (145 satır): `research/atom_lithography_machine/BOM_DETAILED.csv`
- Kanonik sınıf listesi (değişmez): `research/atom_lithography_machine/BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`)
- Tedarikçi teklif teknik şartnameleri (6 paket, BOM varyansının `%92,8`'i): `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md`
- 100k Monte Carlo & EVPI deneyi: `results/exp128_bom_sensitivity/summary_exp128.md` ve `exp128.json`
