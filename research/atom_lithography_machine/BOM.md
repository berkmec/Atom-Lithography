# Atom Litografi Makinesi — Malzeme Listesi (BOM) v2 (`BOM.csv` / `Exp122` Senkronu)

> **Senkron Durumu (2026-11-22):** Bu belge, tek sayısal doğruluk kaynağı olan 40 satırlık `BOM.csv` (`Exp121` seyreltme baz çizgisi, `S6.8=D`) ve `Exp114` / `Exp121` / `Exp122` maliyet-bütçe kapanışıyla birebir eşitlenmiştir.

**Tarih:** 2026-11-22 (v1 tabanı: 2026-10-20; `BOM.csv` senkronu: `Exp121`, 2026-10-26; bütçe tavanı: `Exp122` + 2026-10-26 onayı).  
**Dayanak:** `DESIGN.md` v2.24 (bölüm referansları `[§]`), `BOM.csv` (`40` satır), `Exp65–Exp122`. **Bu liste bir tasarım dokümanıdır; tedarikçi fiyat teklifi, satın alma veya fiziksel üretim iddiası değildir.**  
**Maliyet Sınıfı Sözlüğü (`Exp114` Kalibrasyonu):** `A = 1` (`10³` USD), `B = 10` (`10⁴`), `C = 100` (`10⁵`), `D = 1.000` (`10⁶`) büyüklük-mertebesi sınıf-birimi. `Exp114` halka açık 4-çapa kalibrasyonu: **medyan `$720/birim`**, aralık **`$190–$1.600/birim`** (`8,42×` yayılım — bantlar ±yarım mertebe bulanıktır).  
**Tedarik Sınıfları:** `COTS` (rafta var), `CUS` (özel üretim, bilinen teknoloji), `R&D` (gösterimi olmayan, AR-GE gerekli).

---

## S1 — İyon kaynağı ve demet hazırlama [§3.2] — Ham Toplam: `310,0` birim (`1 B, 3 C`)

| # | Kalem (`BOM.csv` ile birebir) | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S1.1 | Yüksek parlaklıklı iyon kaynağı (LMIS/soğuk iyonizasyon sınıfı) — Exp71: plazma sınıfı yetersiz (B≥4×10⁴ A/m²/sr şart) *(Revizyon Exp81–82/85: duoplazmatron `7,84×` parlaklık + `ΔE ≤ 2 eV` süzgeç ile maliyet sınıfı `C`)* | 2 (P + Si hattı) | R&D | ³¹P⁺/²⁹Si⁺ uyumlu kimya ayrıca AR-GE *(PH₃ gaz güvenliği + `ΔE ≤ 2 eV` süzgeç kodda `ADDERS=+20`)* | C |
| S1.2 | Wien kütle filtresi | 2 | COTS/CUS | ²⁹Si izotop saflığı (Mod A) | C |
| S1.3 | Hızlandırma/yavaşlatma kolonu 5–20 keV ayarlanabilir | 1 | CUS | enerji yayılımı ΔE/E ≤ %1 (Exp66 saçılma bütçesi; P91 `5 keV` çalışma noktası) | C |
| S1.4 | Demet akım geri besleme (Faraday + PID) | 2 | CUS | atış başına doz tekrarlanabilirliği | B |

## S2 — MEMS çok-demet kafası [§3.2] — Ham Toplam: `3.110,0` birim (`1 B, 1 C, 3 D`)

| # | Kalem | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S2.1 | Apertür plakası (Si MEMS, 1 cm² alan) | 1 (+yedek) | R&D | altın bant `10³–10⁴` demetcik (`32 µm` üretim adımı — Exp79); M2'de `10²–10³` | D (geliştirme) |
| S2.2 | Blanker plakası (demetcik başına elektrostatik saptırıcı) | 1 | R&D | kapı süresi ≤1 ms atış çevrimi (Exp65) | D |
| S2.3 | Mini lens dizisi | 1 | R&D | σ_nokta ≤ 2 nm (Exp66 baskın terim; P91 kontratı `σ_nokta ≤ 1,5 nm, Cc ≤ 0,5 mm`) | D |
| S2.4 | Blanker sürücü ASIC/anakartları (kanal başına programlanabilir atış) | dizi boyutunca | CUS | SKY130 türevi kontrol çekirdeği (`Exp58/64` → güncel `blanker_tile` `Exp76–123`; R5 açık) | C |
| S2.5 | Kafa hizalama metrolojisi (kapasitif/optik) | 1 set | CUS | kafa-kademe göreli sapma ölçümü (§5.4) | B |

## S3 — Sayılmış iyon algılama [§4] — Ham Toplam: `210,0` birim (`1 B, 2 C`)

| # | Kalem | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S3.1 | IBIC algılama katmanlı substrat taşıyıcı (pikselli p-i-n diyot dizisi) | yonga başına | CUS | Exp72: C≤0,5 pF ile η≈1; η ≥ 0,9 şart (Exp67; `η(5 keV)=0,9914`) | C |
| S3.2 | Düşük gürültülü yük-amp (CSA) ön uç kartları | kanal sayısınca | CUS | ENC, `5 keV` P91 çalışma noktası iyon yüküne göre (Exp72 yöntemi, Exp91 noktası) | C |
| S3.3 | Sayım kapısı FPGA kartı (blanker geri besleme) | 1 set | COTS/CUS | kapı gecikmesi ≪ atış çevrimi | B |

## S4 — Konumlandırma ve titreşim [§5] — Ham Toplam: `410,0` birim (`1 B, 4 C`)

| # | Kalem | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S4.1 | Granit blok + hava izolatörleri | 1 | COTS | 1–2 Hz köşe | C |
| S4.2 | Aktif sönümleme tablası (jeofon + piezo) | 1 | COTS | 0,5–100 Hz bandı | C |
| S4.3 | Piezo kademe masası (Exp79; maglev kaldırıldı) (6 serbestlik) | 1 | CUS | artık titreşim payı σ_kademe ≤ 0,5 nm hedefi (Exp66; PI PIMars sınıfı UHV) | C |
| S4.4 | Lazer interferometre metroloji (3 eksen) | 1 | COTS | pm sınıfı çözünürlük | C |
| S4.5 | Yonga referans işaretleri + hizalama optiği | 1 set | CUS | atış-anı sapma telafisi | B |

## S5 — Vakum ve süreç — Ham Toplam: `310,0` birim (`1 B, 3 C`)

| # | Kalem | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S5.1 | UHV ana oda + yük kilidi | 1 | CUS | ≤10⁻⁸ mbar sınıfı | C |
| S5.2 | Turbomoleküler + iyon pompa seti | 1 | COTS | — | B |
| S5.3 | Tavlama modülü (hızlı termal, yerinde veya hat-içi) | 1 | COTS | difüzyon bütçesi σ_tavlama (Exp66 ikincil terim) | C |
| S5.4 | ²⁸Si/²⁹Si epitaksiyel substrat tedariği (Mod B banyosu) | parti | CUS | f=%1 ± tolerans (Exp68 sağlam bolluk) | C/parti |

## S6 — Lokal soğutma ve ölçüm adası [§6, §7.2] — Ham Toplam: `2.420,0` birim (`2 B, 4 C, 2 D`)

| # | Kalem | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S6.1 | Kapalı çevrim soğutucu (pulse-tube, 4 K sınıfı) | 1 (altın ölçek: PT420-sınıfı 2,0 W veya 2. PT) | COTS | yalnız yonga adası soğutulur (`S6.8` ön-soğutucu); Exp111 (`@NL58`, 156 hat): 4K okuma yükü `1,48 W @ 7,5 mW` LNA; Exp112 `NL163`'te 56 hat ile `0,55 W @ 7,8 mW`; LNA `≤ 2,8 mW` ise tek PT410 yeter | C |
| S6.2 | Soğuk parmak + radyasyon kalkanları | 1 | CUS | yazma anı termal sapma donması | B |
| S6.3 | Süperiletken mıknatıs (ESR alanı) | 1 | COTS | örnekte `~0,3–1,5 T`; rezonatör düzleminde `≤ 0,4 T` şartı (Exp109, kalkan/offset) | C |
| S6.4 | Mikrodalga hattı (kaynak, IQ modülatör, kriyo zayıflatıcılar) | kanal grubunca | COTS | GRAPE darbe sentezi (Exp61; `ε ≤ 10⁻³` şartı Exp68) | C |
| S6.5 | RF/ENDOR hattı | kanal grubunca | COTS | çekirdek adresleme bantları | B |
| S6.6 | Paralel okuma elektronikleri (frekans çoğullamalı) | R&D ölçeği | R&D | Exp112: altın ölçek `9000` kanal = `56–82` zincir (`NL 110–160`, `Ql 800–1200`; model optimumu `164` ızgara köşesi); termal Exp110–112 ile kapalı; Exp111: LNA `≤ 2,8 mW/hat` (`2,1 mW` InP HEMT çapalı); Exp113: ton gücü `≤ −100 dBm/kanal` (`NL_max=316`; `-90 dBm`'de `32`'ye düşer) | D |
| S6.7 | Tek-elektron okuma (SET/rf-SET) ön uçları | kanal grubunca | CUS/R&D | spin-ölçüm sadakati *(1 K alternatifinde yardımcı-nokta PSB, Exp117–118)* | C |
| S6.8 | **Seyreltme ünitesi (`MXC ~20 mK`; `S6.1` PT ön-soğutma üstüne)** | 1 | COTS | **BAZ kademe (kullanıcı kararı Exp121: maliyet artışı serbest; sağlam seçenek baz).** Exp117 `1 K` sıcak-okuma kolu maliyet-indirme alternatifi olarak sicildedir; implant transferi gösterimi gelirse `C`'ye inebilir | D |

## S7 — Kontrol elektroniği ve hesaplama [§7] — Ham Toplam: `220,0` birim (`2 B, 2 C`)

| # | Kalem | Adet | Sınıf | Kritik şartname | Maliyet |
|---|---|---|---|---|---|
| S7.1 | Ana kontrol bilgisayarı + GPU (GRAPE sentez/seçim) | 1 küme | COTS | yazmaç başına sentez süresi (hesap tarafı) | B |
| S7.2 | AWG kartları (çok kanal) | kanal grubunca | COTS | XY darbe doğruluğu (Exp68 ε bütçesi) | C |
| S7.3 | SKY130 yerel kontrol çipleri (`Exp58` SEG8 / `blanker_tile` hattı) | parti | CUS | 4 K çalışması Exp33 ile karakterize; kapanış R5'te açık | C |
| S7.4 | Senkronizasyon/saat dağıtımı | 1 | COTS | atış-spektroskopi zamanlaması | B |

## S8 — Yazılım [§7, Görev 4] — `4` satır (sınıfsız)

| # | Kalem | Sınıf | Not |
|---|---|---|---|
| S8.1 | `machine_control` fabrika yazılımı (yaz-ölç-seç-kalibre döngüsü) | bu projede yazılır | simülasyon + testlerle teslim |
| S8.2 | Blanker kapı denetleyici RTL (Verilog) + testbench | bu projede yazılır | yosys sentez kontrolü |
| S8.3 | Spektroskopi fit + seçim motoru | Exp48/61 hatlarından taşınır | proje içi kod |
| S8.4 | Sertifika/kayıt veritabanı (atış ve yazmaç kimlikleri) | bu projede yazılır | ürün izlenebilirliği |

## S9 — Sarf ve kalibrasyon — `3` satır (sınıfsız)

| # | Kalem | Sınıf | Not |
|---|---|---|---|
| S9.1 | Kalibrasyon yongaları (bilinen donor desenleri) | CUS | kabul testleri |
| S9.2 | Kaynak sarfiyatı (katot, gaz) | COTS | — |
| S9.3 | Yedek apertür/blanker plakaları | R&D çıktısına bağlı | aşınma bilinmiyor |

---

## Alt Sistem ve Sınıf Özeti (`BOM.csv` Doğrulanmış Aritmetik — `40` Satır)

| Alt Sistem | Satır | B (`10`) | C (`100`) | D (`1000`) | Sınıfsız | Ham Toplam (birim) | Sabit Ham | Değişken Ham | Kanal-Ölçekli (`CHAN_ROWS`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 Kaynak/Demet | 4 | 1 | 3 | 0 | 0 | 310,0 | 310,0 | 0,0 | 0,0 |
| S2 MEMS Kafa | 5 | 1 | 1 | 3 | 0 | 3.110,0 | 10,0 | 3.100,0 | 0,0 |
| S3 IBIC Algılama | 3 | 1 | 2 | 0 | 0 | 210,0 | 210,0 | 0,0 | 100,0 (`S3.2`) |
| S4 Konum/Titreşim | 5 | 1 | 4 | 0 | 0 | 410,0 | 410,0 | 0,0 | 0,0 |
| S5 Vakum/Süreç | 4 | 1 | 3 | 0 | 0 | 310,0 | 310,0 | 0,0 | 0,0 |
| S6 Kriyo/Ölçüm (`S6.8=D` dahil) | 8 | 2 | 4 | 2 | 0 | 2.420,0 | 1.420,0 | 1.000,0 | 210,0 (`S6.4/5/7`) |
| S7 Kontrol/Hesap | 4 | 2 | 2 | 0 | 0 | 220,0 | 220,0 | 0,0 | 100,0 (`S7.2`) |
| S8 Yazılım | 4 | 0 | 0 | 0 | 4 | 0,0 | 0,0 | 0,0 | 0,0 |
| S9 Sarf/Kalibrasyon | 3 | 0 | 0 | 0 | 3 | 0,0 | 0,0 | 0,0 | 0,0 |
| **TOPLAM** | **40** | **9 (`90u`)** | **19 (`1.900u`)** | **5 (`5.000u`)** | **7** | **6.990,0** | **2.890,0** | **4.100,0** | **410,0** |

- **Tedarik sınıfı sayımı (`33` donanım satırı `S1–S7`):** `COTS = 13`, `CUS = 12`, `R&D = 5` (`S1.1, S2.1, S2.2, S2.3, S6.6`), `COTS/CUS = 2` (`S1.2, S3.3`), `CUS/R&D = 1` (`S6.7`).
- **Model yapısal notları (`Exp80`, `Exp83`, `Exp87`, `Exp106`, `Exp114`, `Exp121`):**
  - Kod-içi sabit ekler **`ADDERS = 20,0`** (enerji süzgeci `+B=10` + `PH₃` gaz güvenliği `+B=10`; `BOM.csv` satırı değil, maliyet betiklerinde sabit eklenir).
  - `S6.6` (`D=1000`) maliyet betiklerinde `ceil(ns/NL)·CHAIN_CLASS` zincir-basamak modeliyle değiştirilir (`Exp87+`); `SCALE_ROWS` (`S4.1, S5.1, S5.2, S6.1, S6.3`) zarf `s` ile, `CHAN_ROWS` (`410u`) `(ns/10⁴)^0,7` ile ölçeklenir.
  - v1 (`39` satır, `7.790u`) → v2 (`40` satır, `6.990u`, fark **`−800u`**): `S1.1` `D→C` (`−900`), `S4.3` Maglev `D→Piezo C` (`−900`), yeni `S6.8` seyreltme ünitesi `D` (`+1.000`).

---

## `Exp114` / `Exp121` / `Exp122` Maliyet ve Bütçe Kapanışı (USD Özeti)

**Bağlayıcı Bütçe Kuralı (`Exp122` + 2026-10-26 Kullanıcı Onayı, `H139–H140`):**
- **`≤ 50M USD`:** Normal çalışma bölgesi (gerekmedikçe aşılmaz).
- **`50M–100M USD`:** Yalnız yazılı gerekçeyle izinli (masaüstü `BUTCE_DURUMU.md`'ye işlenmesi şart).
- **`100M USD`:** Kesin üst sınır, aşılamaz.

| Ölçek / Senaryo (`40`-satır `S6.8=D` Baz) | Zincir Sınıfı | Sınıf-Birimi | Altın Oran (`frac`) | BOM USD Min (`@$190/u`) | BOM USD Nominal (`@$720/u`) | BOM USD Max (`@$1600/u`) | Program `×3` (`@$720`) | Program `×10` (`@$720`) | Üçlü-Aşırı `×10` (`@$1600`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Baz Kapısı (`NL55-B`)** | B (`10`) | `2.159,0` *(abs)* | `0,560295` | — | — | — | — | — | — |
| **Ürün (`10⁶/gün, ns=34`)** | B (`10`) | `2.159,0` | — | `$0,410M` | `$1,554M` | `$3,454M` | `$4,66M` | `$15,54M` | `$34,54M` |
| **Ürün (`10⁶/gün, ns=34`)** | Merkez (`16,875`) | **`2.165,9`** | — | `$0,412M` | **`$1,559M`** | `$3,465M` | `$4,68M` | `$15,59M` | `$34,65M` |
| **Ürün (`10⁶/gün, ns=34`)** | C (`100`) | `2.249,0` | — | `$0,427M` | `$1,619M` | `$3,598M` | `$4,86M` | `$16,19M` | `$35,98M` |
| **Altın `NL=163` (`56` zin.)** | B (`10`) | `3.130,6` | `0,495743` | `$0,595M` | `$2,254M` | `$5,009M` | `$6,76M` | `$22,54M` | `$50,09M` |
| **Altın `NL=163` (`56` zin.)** | **Merkez (`16,875`)** | **`3.515,6`** | **`0,521508`** | **`$0,668M`** | **`$2,531M`** | **`$5,625M`** | **`$7,59M`** | **`$25,312M`** *(CT2 PASS)* | `$56,25M` |
| **Altın `NL=163` (`56` zin.)** | C (`100`) | `8.170,6` | `0,686895` | `$1,552M` | `$5,883M` | **`$13,073M`** *(CT1 PASS)* | `$17,65M` | `$58,83M` | **`$130,73M`** *(\>100M uyarısı)* |
| **Altın `NL=67` (`135` zin.)** | B (`10`) | `3.920,6` | `0,544909` | `$0,745M` | `$2,823M` | `$6,273M` | `$8,47M` | `$28,23M` | `$62,73M` |
| **Altın `NL=67` (`135` zin.)** | Merkez (`16,875`) | `4.848,7` | `0,589423` | `$0,921M` | `$3,491M` | `$7,758M` | `$10,47M` | `$34,91M` | `$77,58M` |
| **Altın `NL=67` (`135` zin.)** | C (`100`) | `16.070,6` | `0,776546` | `$3,053M` | `$11,571M` | `$25,713M` | `$34,71M` | `$115,71M` | `$257,13M` |

- **Dürüst Sınırlar:** Mevcut BOM-kapsamı tahminlerinde bütçe aşımı yoktur (`$2,531M` merkez, `$13,073M < $50M` CT1 köşesi, `$25,312M < $100M` CT2 `×10` program çarpanı). Tesis/temizoda, entegrasyon işçiliği ve AR-GE maaşları BOM'da yer almaz; `×3/×10` çarpanları etiketli varsayımlardır. `1 K` sıcak-okuma maliyet-indirme alternatifi (`S6.8 → C`, `Exp117–118`) sabit tabanı `900` birim indirerek `NL163` merkezini `0,447784` / mutlak `1.265,9` birime çeker. `B/C` duvarını daraltacak tek belirleyici adım **kriyo LNA + kriyo izolatör + seyreltme ünitesi tedarikçi teklifleridir.**
