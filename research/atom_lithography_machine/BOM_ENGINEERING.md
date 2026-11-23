# Atom Litografi Makinesi — Parça-Düzeyi Mühendislik BOM Analizi (`BOM_ENGINEERING.md` — `v4.0`)

> **Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Bu belge, kanonik 40 satırlık `BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` — kesinlikle değiştirilmemiştir) dosyasının `BOM_DETAILED.csv` altında **`v4.0` için 159 fiziksel parça/alt-montaj satırına** (`145` `v3.0` + `14` `v4.0` parça) açılmış mühendislik çözümlemesidir. **Hiçbir satır gerçek tedarikçi fiyat teklifi değildir.** Tüm USD değerleri `M3 v4.0` Altın Ölçek (`NL=163`, `56` okuma zinciri, `Arch-B` eş-adımlı `0,50 mm` / `32×32 = 1.024` demetcik [`16×` 64-ch karo], `s=0,5` zarf, `S6.8=20 mK` seyreltme baz kademesi + `v4.0` donanım paketi: `S5.5` flaş-tavlama, `S6.9` `PT420` titreşim ayrıştırma, `S6.10` `M4` kavite-QED veri yolu & `4 K` `968`-kapı çapraz-anahtar, `S7.1-04` BOED GPU düğümü) için satır-genişletilmiş toplamlar olup `{Liste-Çapası}` (`%9,1`), `{Model-Kalibrasyon-Exp114}` (`%52,7`), `{Varsayım}` (`%38,2`) veya `{Program-NRE-Kapsam}` (`S8` yazılım, `$0` donanım alımı) etiketlidir.

**Tarih:** 2026-11-23 *(`v4.0` tam fizik & ekonomi senkronu: `Exp124–Exp134`)*  
**Dayanak:** `BOM.csv` (`Exp121/122` kanonik baz), `BOM_DETAILED.csv` (`159` parça), `Exp85–Exp122` maliyet zinciri, `Exp124` (`Arch-B` `10→5 keV` yavaşlatma + `HDA-HiRes R₀=40 mm, ΔE_FWHM=0,453 eV` + Wien `0,45 T, 150 mm`), `Exp125` (`8`-bobinli `Ø150 mm` bore / `36 mm` yarık / `Ø352 mm` OD `1,500000 T ±17,8 ppm` kriyo-mıknatıs + `Nb RRR>300` kalkan `22,3 µT` / `64,6 K` quench), `Exp127` (`100 K` `LTC6268` CSA `1,2 µs / 1 GΩ, ENC=24,1 e⁻, η=0,99936`), `Exp128` (`100.000` örneklemli korelasyonlu MC), `Exp130` (`S5.5` `808 nm / 1,0 ms` flaş-tavlama, `f_act=%99,98, σ_anneal=0,328 nm`), `Exp131` (`M4` `3 kΩ` `NbTiN` `L_res=300 µm` kavite-QED veri yolu + `Δz_cap*=8±1 nm` `²⁸Si` kaplama + `4 K` `968`-kapı çapraz-anahtar), `Exp132` (BOED Bayesyen spektroskopi), `Exp133` (`PT420` uzak döner valf + `2.000 N/m` CF63 körük + `4×` OFHC Cu örgü `52,7 N/m` + `25 dB` FF, `σ_stage=0,1024 nm, σ_pointing=0,1473 nm`), `Exp134` (`+$420k` `v4.0` fab TCO ve birim ekonomi kapanışı).

---

## 1. Yönetici Özeti ve `BOM.csv` (`Exp122`) → `M3 v3.0` → `M3 v4.0` Uzlaştırması

Kanonik `BOM.csv` (`40` satır) büyüklük-mertebesi sınıf modeliyle (`Exp114` medyan `$720/birim`) `M3` altın ölçekte **`$2.531.244`** (`3.515,62` sınıf-birimi; aralık `$0,595M–$13,073M`) verir. Parça düzeyinde `BOM_DETAILED.csv` `v3.0` tabanı (`145` parça) **`$4.189.600`** nominal iken, **`v4.0`** donanım yükseltme paketinin (`13` donanım + `1` `$0` yazılım satırı = **`+$420.000`** nominal `[$235k–$782k]`, `Exp134` ile birebir) eklenmesiyle **`BOM_DETAILED.csv v4.0` (`159` parça; `40/40` kanonik kimlik + `S1.5, S1.6, S5.5, S6.9, S6.10` ek mühendislik paketleri)** tam olarak **`$4.609.600`** nominal (`$2.564.000` P10 alt – `$8.616.700` P90 üst) donanım toplamına ulaşır (**`$0,00` uzlaştırma hatası**).

### 1.1 Alt-Sistem Bazlı Tam Uzlaştırma Tablosu (`Exp122` vs `M1 v4.0` vs `M3 v4.0`)

| Alt Sistem | Parça Sayısı | `Exp122` Kanonik (`@$720/u`) | `M1 v4.0` Prototip (Nom `[P10–P90]`) | `M3 v4.0` `BOM_DETAILED` (Nom `[P10–P90]`) | `M3 − Exp122` Farkı (`Δ`) | Farkın Kök Mühendislik Nedeni |
|---|---:|---:|---:|---:|---:|---|
| **S1** Kaynak & Kolon | 22 | `$237.600` | `$319.750` `[$183k–$585k]` | `$416.000` `[$238k–$762k]` | **`+$178.400`** | `Exp124` `Arch-B` `10→5 keV` yavaşlatma (`WD=0,250 mm, C_c=2,660 mm`, `+$28k`) + `HDA-HiRes` (`R₀=40 mm, ΔE_FWHM=0,453 eV`, `S1.5`, `$62k`) + Wien (`0,45 T, 150 mm`) + `PH₃` kabin/yıkayıcı (`S1.6`, `$58k`) |
| **S2** MEMS Çok-Demet Kafa | 18 | `$10.633` | `$147.750` `[$80k–$289k]` | `$775.500` `[$392k–$1.606k]` | **`+$764.867`** | **En büyük yapısal açık:** `Exp122` `(nb/10⁶)^0,7` ölçeğinin ezdiği sabit MEMS fab/NRE (`$370k` NRE + `$291k` plakalar/`Arch-B` lens/interposer + `$115k` SKY130/metroloji) açılır |
| **S3** IBIC Algılama | 14 | `$146.081` | `$88.550` `[$48k–$168k]` | `$224.000` `[$120k–$428k]` | **`+$77.919`** | `Exp127` kilitli `100 K` soğuk-ada (`COLD_100K`) `16×8` `LTC6268` CSA (`1,2 µs / 1 GΩ, Q_ion~342 e⁻, ENC=24,1 e⁻, η=0,99936 @ 5 keV`) + trim DAC + `<5 cm` mikro-koaksiyel |
| **S4** Konum & Titreşim | 17 | `$241.200` | `$233.920` `[$142k–$411k]` | `$253.000` `[$152k–$446k]` | **`+$11.800`** | `Exp122` ile `%4,9` içinde uyum (`Renishaw XL-80` + `PI PIMars` UHV piezo + aktif tabla + Invar çerçeve) |
| **S5** Vakum, Süreç & `S5.5` Flaş | 20 | `$163.800` | `$263.300` `[$152k–$480k]` | `$338.000` `[$193k–$619k]` | **`+$174.200`** | `v3.0` UHV/pompa/load-lock (`+$79,2k`) + **`v4.0` `S5.5` Flaş-Tavlama Optik Kafası (`Exp130`, `+$95,0k`: `808 nm` qCW homojenleştirici, CF63 safir, `10 µs` pirometre, deklanşör kilidi)** |
| **S6** Kriyo, DR, Mıknatıs, Okuma, `PT420` & `M4` | 38 | `$1.578.650` | `$1.124.300` `[$666k–$1.980k]` | `$2.238.900` `[$1.268k–$4.058k]` | **`+$660.250`** | `S6.6` 56-zincir (**`$680.400`**) ve `S6.8` 20 mK DR (**`$720.000`**) `Exp114/122` ile **kuruşu kuruşuna eşit**; `v3.0` `Exp125` mıknatıs+NbTiN+`PT420` (`+$347,3k`) + **`v4.0` `S6.9` `PT420` Ayrıştırma (`Exp133`, `+$68,0k`) + `S6.10` `M4` Kavite-QED Veri Yolu (`Exp131`, `+$245,0k`)** |
| **S7** Kontrol, Hesaplama & BOED GPU | 14 | `$153.281` | `$116.450` `[$67k–$214k]` | `$216.200` `[$122k–$400k]` | **`+$62.919`** | `v3.0` `2× Lambda Vector` + AWG + SKY130 + EMI/PLC (`+$50,9k`) + **`v4.0` `S7.1-04` `S8` BOED Gerçek-Zamanlı Bayesyen GPU Düğümü (`Exp132/134`, `+$12,0k`)** |
| **S8** Yazılım & RTL (`+BOED`) | 9 | `$0` | `$0` | `$0` | **`$0`** | Proje-içi yazılım/RTL (`machine_control v3/v4`, `CellISA`, `blanker_tile`, GRAPE/XY8 + **`S8.3-03` BOED motoru**); mühendislik işçiliği Program `×3–×10` NRE içindedir |
| **S9** Sarf & Yedekler | 7 | `$0` | `$42.250` `[$22k–$82k]` | `$148.000` `[$78k–$297k]` | **`+$148.000`** | Kalibrasyon yongaları (`$35k`), 1 yıllık gaz/katot sarfı (`$18k`), yedek MEMS plakaları + 4 yedek kriyo-LNA zinciri + kriyostat bakım kiti (`$95k`) |
| **TOPLAM (`v4.0`)** | **159** | **`$2.531.244`** | **`$2.336.270`** `[$1,36M–$4,21M]` | **`$4.609.600`** `[$2,56M–$8,62M]` | **`+$2.078.356`** | **Uzlaştırma hatası: `$0,00` (`M3 v3.0 = $4.189.600` + `v4.0 delta = +$420.000`)** |

### 1.2 Kurumsal Delta Köprüsü (`Exp122` `$2,531M` → `M3 v3.0` `$4,190M` → `M3 v4.0` `$4,610M`)

| Köprü Adımı | Tutar (USD) | Toplam Artıştaki Pay | Açıklama |
|---|---:|---:|---|
| **`Exp122` Merkez Bazı (`3.515,62u @ $720`)** | `$2.531.244` | — | `40` kanonik satır, `S6.8=D (20 mK)`, `NL=163`, merkez zincir `16,875` |
| `+ S2` MEMS Sabit Maske / DRIE / TSV / Bonding NRE | `+$764.867` | `%36,8` | `Exp122` üssel ölçeğinin bastırdığı sabit MEMS geliştirme donanımı |
| `+ COTS / UHV / PT420 / EMI` Gerçek Çapa Uyumu | `+$285.769` | `%13,7` | Yeni `PT420`, `S5.2` pompa çapası, UHV vana/transfer, `S7` EMI/PLC |
| `+ Exp125` `1,5 T / ≤0,4 T` Mıknatıs + Nb Kalkan + NbTiN | `+$261.000` | `%12,6` | Aktif karşı-sargılı bobin + Nb/Cryoperm kalkan (`+$176k`) + 9000 NbTiN çip (`+$85k`) |
| `+ S9` Kalibrasyon Yongaları, Gaz & Yedek MEMS/LNA | `+$148.000` | `%7,1` | `BOM.csv`'de sınıfsız olan operasyonel donanım |
| `+ Exp124` `10→5 keV` Yavaşlatma + `HDA-HiRes` (`0,453 eV`) + `PH₃` | `+$133.600` | `%6,4` | `Exp83` `ADDERS=+20u ($14,4k)` üzerine gerçek `HDA-HiRes` UHV süzgeç + scrubber + `Arch-B` lens |
| `+ Exp127` Kilitli `100 K` `16×8` Düşük-C `LTC6268` IBIC Ön-Uç | `+$65.119` | `%3,1` | `100 K / 1,2 µs / 1 GΩ` (`342 e⁻, η=0,99936`) CSA + kanal-başı trim DAC + `<5 cm` mikro-koaksiyel |
| **`= M3 v3.0` Ara Toplam (`145` parça)** | **`$4.189.600`** | **`%79,8`** | `Exp134` `v3.0` taban çapasıyla `$0,00` sapma |
| **`+ v4.0` Yükseltme Paketi (`Exp130/131/132/133/134`, `13` HW parça)** | **`+$420.000`** | **`%20,2`** | `S6.10` `M4` veri yolu (`$245k`) + `S5.5` flaş-tavlama (`$95k`) + `S6.9` `PT420` ayrıştırma (`$68k`) + `S7.1-04` BOED GPU (`$12k`) |
| **`= M3 v4.0 BOM_DETAILED` Nominal Donanım Toplamı (`159` parça)** | **`$4.609.600`** | **`%100,0`** | **`$50M` yumuşak bütçe çizgisinin `10,8×`, `$100M` sert sınırın `21,7×` altında** |

### 1.3 `v4.0` Donanım Paketi Alt-Parça Kırılımı (`+$420.000` Nominal, `$235k–$782k`, `Exp134` Birebir)

| Paket & Kaynak Deney | Parça Kimlikleri (`BOM_DETAILED.csv`) | Alt-Parça Özeti & Kilitli Mühendislik Şartnamesi | `P10 / P50 / P90` (USD) | RFQ Paketi |
|---|---|---|---:|---|
| **`S5.5` Flaş-Tavlama Optik Kafası (`Exp130`)** | `S5.5-01..04` (`4` parça) | `808 nm` qCW bar + `84×88×84 mm` düz-tepe homojenleştirici (`41,15 J/cm², 1,0 ms, 1440,3 K, f_act=%99,98, σ_anneal=0,328 nm`), `+Y` CF63 safir (`Ø44 mm CA, T_AR=%98,0, 9,47× LIDT`), `10 µs` dikroik pirometre + `±%1,5` enerji integratörü, MXC `<1 K` + UHV vana deklanşör kilidi | `$55k / $95k / $175k` | **RFQ-07** |
| **`S6.9` `PT420` Titreşim Ayrıştırma (`Exp133`)** | `S6.9-01..04` (`4` parça) | `500 mm` ofsetli uzak döner valf + `600 mm` esnek He hattı, kenar-kaynaklı `316L` CF63 OVC körük (`ID=44/OD=68/L=120 mm, k=2.000 N/m`), `Ø12×397 mm` bara + `4×` S-ilmek OFHC Cu örgü (`k=52,7 N/m, ΔT=3,7 mK`), `1,4–21 Hz` `25 dB` harmonik FF DSP (`σ_stage=0,1024 nm, σ_pointing=0,1473 nm`) | `$38k / $68k / $125k` | **RFQ-07** |
| **`S6.10` `M4` Kavite-QED Veri Yolu (`Exp131`)** | `S6.10-01..04` (`4` parça) | `3 kΩ` `NbTiN` (`t=9 nm, w=100 nm, L_□=100 pH/□, L_res=300 µm, B_M4=0,1785 T`) veri yolu yongası, `Δz_cap*=8±1 nm` `²⁸Si` düşük-T epi kaplama (`%95,20` sweet-spot), `4 K` `SKY130` `968`-kapı çapraz-anahtar çoklama kartı (`L=11 FT %99,40`), `5 GHz` + düşük-gürültülü DC kapı elektroniği | `$135k / $245k / $460k` | **RFQ-07** |
| **`S7.1-04` (`S8`) BOED GPU Düğümü (`Exp132/134`)** | `S7.1-04` (`1` HW) + `S8.3-03` (`$0` SW) | Gerçek-zamanlı Bayesyen uyarlamalı spektroskopi çıkarım GPU düğümü (`5×–10×` okuma hızlanması, `<1 ms` posterior güncelleme) + proje içi `machine_control v3/v4` BOED yazılım motoru | `$7k / $12k / $22k` | Non-RFQ (COTS) |
| **TOPLAM `v4.0` DELTASI** | **`13` HW + `1` SW Parça** | **`CAD v4.0` & `Exp130–Exp134` tam donanım kapanışı (`+%10,02` HW)** | **`$235k / $420k / $782k`** | **`RFQ-07 = $408k`** |

---

## 2. Malzeme, Vakum, Kriyojenik ve Manyetik Uyumluluk Matrisi (`v4.0`)

Atom litografi makinesi aynı fiziksel zarf içinde dört aşırı fiziksel rejimi birleştirir: **UHV (`≤ 10⁻⁹ mbar`, `150 °C` bakeout)**, **kriyojenik 5 kademe (`300 K → 50 K → 4 K → Still 0,8 K → CP 100 mK → MXC 20 mK`)**, **yüksek/sıfır manyetik alan geçişi (`1,50 T` ESR/ENDOR veya `0,1785 T` `M4` kipi ↔ `22,3 µT` kalkanlı rezonatör düzlemi ↔ `< 1 µT` iyon kolonu)** ve **toksik/piroforik `PH₃` gazı**.

| Bölge / Sıcaklık Kademesi | Kapsanan Parçalar (`BOM_DETAILED v4.0`) | Vakum / Basınç Rejimi | Onaylı Yapısal & İletken Malzemeler | Yasaklı / Riskli Malzemeler & Kritik Kısıtlar |
|---|---|---|---|---|
| **Kaynak & `PH₃` Hattı (`300 K`, su soğutmalı)** | `S1.1`, `S1.2`, `S1.6`, `S9.2` | Kaynak `10⁻⁶ mbar` → diferansiyel `10⁻⁹ mbar`; egzoz negatif basınç | `316L VAR` (EP), Molibden anot, `Al₂O₃`, metal VCR contalar | Pirinç/elastomer `PH₃` hattında **yasak**; `≤ 10⁻¹⁰ mbar·L/s`; `50 ppb` PLC acil kapama (`S7.4-04`) |
| **İyon Kolonu, MEMS Kafa & `S5.5` Flaş (`300 K`, UHV)** | `S1.3–1.5`, `S2.1–2.5`, `S5.1–5.5` | UHV `≤ 10⁻⁹ mbar`, `150 °C` bakeout | `316LN`, `Ti-6Al-4V`, katkılı Si (SOI), `Au/Pt`, Safir (`Ø50×8 mm`, `T_AR=%98,0 @ 808 nm`), `AlN`, `LTCC`, `Kapton` | Ferromanyetik çelik ve gaz çıkışlı epoksi **yasak**; `S5.5` `F_win=10,56 J/cm²` (`9,47× LIDT`), MXC `<1 K` deklanşör kilidi zorunlu (`Exp130`) |
| **Konum & Metroloji (`300 K`, UHV + Atmosfer)** | `S4.1–4.5` | Kademe/ayna UHV `10⁻⁹ mbar`; granit/aktif tabla atmosfer | Siyah granit, `Invar-36` (`CTE ≤ 1,2 ppm/K`), `Zerodur/ULE`, manyetik olmayan `Ti` piezo flekstür | Manyetik paslanmaz piezo kademede **yasak**; temizoda zemini en az **`VC-E` (`3,1 µm/s`)** zorunlu (`Exp133` `CY5`) |
| **Vakum-İçi IBIC Ön-Uç (`100 K` Soğuk Ada, UHV)** | `S3.1–3.2` (`Exp127`) | UHV `10⁻⁹ mbar` | Yüksek-direnç Si (`>10 kΩ·cm`), Safir/AlN, `BeCu+Au`, `Rogers 4350B`/`Al₂O₃`, `COLD_100K` `LTC6268` CSA (`1,2 µs / 1 GΩ, ENC=24,1 e⁻, η=0,99936`) | FR4 vakumda **yasak**; kablo boyu `< 5 cm` (`C_par < 0,15 pF` → `C_tot ≤ 0,5 pF`, `Exp72/127`) |
| **Kriyo Kalkan, `4 K` Kademe & `PT420` Ayrıştırma (`50 K / 4 K`)** | `S6.1–6.5`, `S6.6-01/02`, `S6.9-01/02/04`, `S6.10-03`, `S7.3` | Kriyo-vakum `≤ 10⁻⁷ mbar` | Tavlanmış `OFHC Cu` (`RRR ≥ 200`), `316L` kenar-kaynaklı CF63 körük (`k=2.000 N/m`), `8`-bobin `NbTi/Cu`, `Bi-2223 HTS`, `4 K` `SKY130` `968`-kapı çapraz-anahtar | Rijit `OVC` köprüsü (`4,96 MN/m`) ve kafa-üstü `PT420` valfi **yasak** (`2.052 nm` titreşim yaratır, `Exp133`); `4 K` okuma yükü `≤ 1,5 W` (`PT420`) |
| **Manyetik Geçiş, `M4` Veri Yolu & `MXC 20 mK` Adası** | `S6.3-02/03`, `S6.6-04/07`, `S6.7`, `S6.8`, `S6.9-03`, `S6.10-01/02` | UHV / Kriyo-vakum (`20 mK`) | `4×` S-ilmek OFHC Cu örgü (`k=52,7 N/m, ΔT=3,7 mK`), `Nb (RRR>300)` + `Cryoperm-10`, `3 kΩ` `NbTiN` (`t=9 nm, w=100 nm, L_res=300 µm`), `Δz_cap*=8±1 nm` `²⁸Si` kaplama | Rijit `Ø7×497 mm` Cu çubuk (`9,06 MN/m`) ve Nikel kaplı SMA `MXC`'de **yasak**; `M4` kipi **`B_M4 = 0,1785 T`** (`0,30 T` `NbTiN` sınırının `%40,5` altında; `Exp131`) |

---

## 3. Tedarik Sınıfı (`COTS / CUS / R&D`) ve Tedarik Zinciri Risk Haritası (`v4.0`)

### 3.1 `BOM_DETAILED.csv v4.0` Tedarik ve Epistemik Dağılımı (`159` Parça)

| Tedarik Sınıfı | Parça Sayısı | `M3 v4.0` Alt (`P10`) | `M3 v4.0` Nominal (`P50`) | `M3 v4.0` Üst (`P90`) | `M3 v4.0` Nominal Payı | Tipik Teslim Süresi (Varsayım) |
|---|---:|---:|---:|---:|---:|---|
| **`COTS`** (Rafta/Katalog) | 65 | `$1.023.200` | `$1.736.200` | `$3.062.200` | **`%37,7`** | 4–24 hafta *(DR `S6.8`: 26–44 hafta)* |
| **`CUS`** (Özel Üretim, Bilinen Teknoloji) | 56 | `$704.800` | `$1.275.400` | `$2.370.500` | **`%27,7`** | 12–36 hafta |
| **`R&D`** (Gösterimsiz / AR-GE Gerekli) | 12 | `$560.000` | `$1.108.000` | `$2.277.000` | **`%24,0`** | 6–24 ay *(iteratif)* |
| **`COTS/CUS`** (Katalog Uyarlama) | 13 | `$173.000` | `$301.000` | `$542.000` | `%6,5` | 8–20 hafta |
| **`CUS/R&D`** (Özel + AR-GE Sınırı) | 4 | `$103.000` | `$189.000` | `$365.000` | `%4,1` | 16–36 hafta |
| **`IN-HOUSE`** (`S8` Yazılım/RTL + BOED) | 9 | `$0` | `$0` | `$0` | `%0,0` *(HW)* | Proje içi geliştirme (`Program NRE`) |
| **TOPLAM (`v4.0`)** | **159** | **`$2.564.000`** | **`$4.609.600`** | **`$8.616.700`** | **`%100,0`** | — |

- **Epistemik Dağılım (`M3 v4.0` Nominal):** `{Liste-Çapası}`: `15` parça (`$417.400`, `%9,1`) | `{Model-Kalibrasyon-Exp114}`: `93` parça (`$2.429.700`, `%52,7`) | `{Varsayım}`: `42` parça (`$1.762.500`, `%38,2`) | `{Program-NRE-Kapsam}`: `9` parça (`$0`).

### 3.2 Kritik Tedarik Risk Matrisi & Azaltım Stratejileri (`v4.0`)

| Öncelik | Risk Kalemi (`BOM_DETAILED v4.0`) | Maliyet Varyansı / Etkisi (`Exp128 v4.0`) | Tek-Kaynak / Darboğaz Riski | Somut Azaltım Eylemi |
|---|---|---|---|---|
| **P0 (KRİTİK)** | **`S6.6-01/02` 56× Kriyo-LNA (`≤2,8 mW`) + İzolatör (`B/C` Duvarı)** | **BOM varyansının `%73,4`'ü** (`ρ=0,886`, P10–P90 salınımı `$9,16M`) | `100–900 MHz` `≤2,1 mW` InP HEMT katalog parçası değil; LNF/QMC teklif usulü | **RFQ-05'i hemen gönder;** 100–900 MHz SiGe veya `4–8 GHz` yükseltilmiş bant + `PT420` (`7,8 mW` LNA uyumlu) opsiyonunu sor |
| **P1 (YÜKSEK)** | **`S2.1–S2.3` MEMS Apertür / Blanker / `Arch-B` Mini-Lens NRE** | Varyansın `%6,0`'ı (`$661k` nom, `$1,39M` P90) | 3-yonga hizalı `Arch-B` (`0,50 mm` eş-adımlı `32×32 = 1.024`, `WD=0,250 mm`) sayılı MEMS dökümhanelerinde yapılır | **RFQ-02 ile aşamalı M1→M2→M3:** M1 tek-delik/FIB (`$148k`), M2 `8×8–16×16`, M3 `32×32 = 1.024` |
| **P1 (YÜKSEK)** | **`S6.8` `20 mK` Seyreltme Kriyostatı + `³He` İzotop Şarjı** | Varyansın `%5,3`'ü (`$720k` nom, `$1,25M` P90) | 26–44 hafta teslim süresi; `³He` piyasası oynak | **RFQ-06'yı erken siparişle kilitle;** `1 K` AR-GE'sini filo (`N ≥ 6`) ölçeğine ertele (`Exp128 CU5`) |
| **P1 (YÜKSEK)** | **`v4.0` Paketi: `S5.5` Flaş + `S6.9` `PT420` + `S6.10` `M4` (`RFQ-07`)** | Varyansın `%3,4`'ü (`$420k` nom, `#4` sürücü) | `3 kΩ` `NbTiN` (`w=100 nm`) + `8±1 nm` düşük-T `²⁸Si` kaplama özel foundry; `PT420` körük/örgü DR arayüzüne kilitli | **RFQ-07'yi üç alt-paket olarak dağıt:** (7A) lazer/optik, (7B) DR/körük üreticisiyle ortak mekanik ICD, (7C) süperiletken/epi foundry |
| **P2 (ORTA)** | **`S6.3` `1,50 T / ≤0,40 T` Mıknatıs (`Exp125`) & `S5.4` Epi** | Mıknatıs `$185k` (`%1,5` var.), Epi `$56k` | Özel `NbTi` karşı-sargı + `Nb/Cryoperm` kalkan; `²⁸SiH₄` arzı sınırlı | **RFQ-04 ile RFQ-06 (DR) ortak ICD;** M1'de 5-yonga deneme epi lotu (`$16,8k`) |

---

## 4. Aşamalı Maliyet Kırılımı: `M1 v4.0` Tek-Demet Prototip vs. `M3 v4.0` Altın Ölçek

| Boyut / Alt Sistem | `M1 v4.0` Tek-Demet Prototipi | `M3 v4.0` Altın Ölçek (`BOM_DETAILED`) | `M1 / M3` Oranı | `M1 → M3` Temel Fark |
|---|---:|---:|---:|---|
| **Demetcik / Okuma / `M4`** | `1` demetcik / `2` zincir / tek-donör | `32×32 = 1.024` demetcik / `56` zincir / `M4` `3 kΩ` veri yolu | — | Paralelleştirme + `M4` çok-kübit geçişi |
| **`S1` Kaynak & Kolon** | `$319.750` | `$416.000` | `%76,9` | Yalnız `³¹P⁺` hattı; `HDA-HiRes` (`0,453 eV`) + `PH₃` + `10→5 keV` kolon korunur |
| **`S2` Kafa / Odak** | `$147.750` | `$775.500` | `%19,1` | Tek-delikli FIB/pinhole + tek-eksen Einzel lens (çok-demet MEMS NRE M2'de) |
| **`S3` IBIC Algılama** | `$88.550` | `$224.000` | `%39,5` | `1–2×8` ch `100 K` IBIC modülü + tek CF63 + tek FPGA |
| **`S4` Konum & İnterferometri** | `$233.920` | `$253.000` | `%92,5` | `σ ≤ 0,5 nm` piezo + aktif izolasyon + 2-eksen interferometri M1'de de zorunlu |
| **`S5` UHV, Süreç & `S5.5` Flaş** | `$263.300` | `$338.000` | `%77,9` | UHV + `M1 G4` kompakt Mod-2 `4×4 mm` `S5.5` flaş başlığı + tam CF63 safir/pirometre/kilit |
| **`S6` Kriyo, DR, Mıknatıs, `PT420`, `M4`** | `$1.124.300` | `$2.238.900` | `%50,2` | `20 mK` DR (`$720k`) + **`PT420` ayrıştırma (`S6.9`, `$68k` tam!)** + `1,5 T` mıknatıs M1'de; 56-zincir (`−$656k`) & `M4` veri yolu (`S6.10`, `−$245k`) M3/M4'te |
| **`S7` Kontrol & BOED GPU** | `$116.450` | `$216.200` | `%53,9` | 1× GPU + **`1× S7.1-04` BOED GPU (`$12k`)** + 1× AWG + 1× EMI kabin |
| **`S9` Sarf & Yedekler** | `$42.250` | `$148.000` | `%28,5` | Yarı kalibrasyon/gaz kiti (çok-demet MEMS yedekleri M2/M3'te) |
| **TOPLAM DONANIM (`P50 [P10–P90]`)** | **`$2.336.270`** `[$1,36M–$4,21M]` | **`$4.609.600`** `[$2,56M–$8,62M]` | **`%50,7`** | **M1 donanımının `>%83`'ü M3 `v4.0`'a doğrudan taşınabilir demirbaştır!** |
| **Tahmini Program (`×3` – `×5,5` – `×10`)** | `$7,0M` – `$12,8M` – `$23,4M` | `$13,8M` – `$25,3M` *(MC P50 `$30,9M`)* – `$46,1M` *(MC P50 `$55,0M`)* | — | M1 programı en sert `×10` varsayımında bile `$50M` çizgisinin yarısının altındadır |

---

## 5. Çapraz Referanslar

- Parça listesi (`v4.0`, `159` satır): `research/atom_lithography_machine/BOM_DETAILED.csv`
- Kanonik sınıf listesi (değişmez): `research/atom_lithography_machine/BOM.csv` (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`)
- Tedarikçi teklif teknik şartnameleri (`7` paket = `RFQ-01..RFQ-07`, BOM varyansının `%92,6`'sı): `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md`
- 100k Monte Carlo & EVPI deneyi (`v4.0`): `results/exp128_bom_sensitivity/summary_exp128.md` ve `exp128.json`
- Fab TCO, birim ekonomi (`$/kübit`) & Wright öğrenme eğrisi: `results/exp134_fab_economics_tco/summary_exp134.md` ve `exp134.json`
