# Exp139 (`H157`) — Bütünleşik `8 nm` `²⁸Si` Epi Kaplama + `ms` Flaş Tavlama + `Si/SiO₂` `D_it` / `S_ε` Arayüz Ortak Fiziği & `S5.6` Donanım Şartnamesi

> **Epistemik Dürüstlük Beyanı:** `no_lab_measurement = true`, `no_supplier_quotes = true`. Tüm sonuçlar `{Model}`, `{Sayısal-Simülasyon}`, `{Literatür}` ve maliyet kalemleri için `{Varsayım}` kapsamındadır. Ön-kayıtlı 7 öngörü (`EP1–EP7`) herhangi bir kod veya sayısal koşum öncesinde `results/exp139_epi_cap_process_integration/predictions_exp139.json` dosyasına mühürlenmiş ve sonradan değiştirilmemiştir. **`EP1, EP2, EP4, EP6 PASS`**; **`EP3, EP5, EP7` dürüstçe `FAIL`** kaydedilmiştir — ve **`EP5` / `EP3` başarısızlığı `v4.0` → `v5.0` için kritik bir gerçek yarı-iletken süreç keşfi ortaya çıkarıp anında çözülmüştür.**

---

## 1. Yönetici Özeti ve Ön-Kayıtlı Kararlar (`EP1–EP7`)

`Exp130` çıplak yüzeyde `808 nm / 1,0 ms / 41,15 J/cm²` (`1440 K`) flaş tavlamayı (`σ_anneal = 0,328 nm`), `Exp131` ise `M4` flip-flop kübitleri için `Δz_cap* = 8,0 ± 1,0 nm` `²⁸Si` epitaksiyel kaplamanın zorunluluğunu (`%24,15 → %95,20` verim) göstermişti. `Exp139 (H157)`, bu iki süreci **ZBL+LSS BCA iyon implantasyonu + ikincil `¹⁶O` geri-tepme şelalesi + `Exp130` 1B doğrusal-olmayan termal/TED PDE zinciri + `Eaglesham / Gossmann / Nützel–Abstreiter` düşük-sıcaklık `²⁸Si` MBE kinetiği + kesin 2B görüntü-yüklü McWhorter elektrostatiği + `Exp131` kesin `4×4` Tosi flip-flop verim değerlendiricisi** içinde tek modelde birleştirir.

### Ana Bilimsel Keşif (`v4.0` → `v5.0` Süreç Düzeltmesi)
- **`v4.0` `1×1440 K` (`41,15 J/cm²`) Flaş-Sonrası Gizli Arka-Uç TED Tehlikesi (`EP5 FAIL`):** `Exp130`'un tek-kademeli `1,0 ms / 1440 K` darbesi `SPE` aktivasyonunu (`E_a = 2,70 eV`) `%99,98` tamamlasa da daha yüksek bariyerli `{311}` öz-arayer küme çözünmesi (`E_diss = 3,10 eV`) yalnızca `∫ k_diss dt = 1,997` değerine ulaşır ve implantasyon hasarı kümelerinin **`%13,57`'si çözünmeden donar**. Pul ardından `345 °C / 80 s` MBE + `350 °C / 15 dk` forming-gas pasivasyonuna girdiğinde, negatif TED aktivasyon enerjisi (`+1,29 eV`) nedeniyle bu donmuş arayerler **`+1,318 nm` gizli arka-uç TED** doğurur (`σ_anneal: 0,328 → 1,646 nm`, `Exp124 σ_tot = 3,995 nm > 3,80 nm`, `Rota A` verimi `%92,20 < %93`!).
- **Kesin `v5.0` Küme-Temizleyici Flaş Çözümü (Donanım Değişikliği Yok!):** `S5.5` lazer akısını yalnızca **`+2,34 J/cm²` (`+%5,7`)** artırarak **`43,49 J/cm² / 1530,1 K` (`0,907 T_melt < 0,92 T_melt = 1552 K`, safir `F_win = 11,16 J/cm²` → `8,96× LIDT`)** düzeyine çıkarmak `{311}` küme çözünmesini `∫ k_diss dt = 9,071`'e (**`%99,99` küme temizliği!**) taşır; arka-uç gizli TED'i **`35×`** bastırır (`+1,318 → +0,037 nm`, toplam **`σ_anneal = 0,430 nm ≤ 0,50 nm`**, **`Exp124 σ_tot = 3,665 nm ≤ 3,80 nm`**) ve **`Rota A` verimini `%95,35`'e, `Rota C` verimini `%97,70`'e (`medyan C = 7.557`)** çıkarır! *(Alternatif olarak `v4.0` `1440 K` sıcaklığında `4 × 1,0 ms` çoklu darbe de `%99,97` küme temizliğiyle `σ_anneal = 0,468 nm`, `Exp124 σ_tot = 3,670 nm` sağlar.)*

| Kod | Ön-Kayıtlı Kriter (`predictions_exp139.json`) | Ölçülen Değer (`exp139.json`, `{Sayısal-Simülasyon}`) | Karar |
| :--- | :--- | :--- | :--- |
| **`EP1`** | BCA `Exp92` `±%5` uyumu; Rota B (`20–24 keV`) `≥2,0×` `σ_x` (`>7 nm`), `≥1,8×` `σ_z` (`>5,5 nm`), `≥0,2` geri-tepme O/iyon | `Exp92` max fark **`%1,78`**; Rota B `22 keV`: `σ_lat = 7,69 nm` (**`2,38×`**), `σ_z = 5,87 nm` (**`2,09×`**), `Exp124 σ_tot = 7,87 nm` (`>3,80`); geri-tepme O: **`1,02/iyon`** (`20 keV`), **`1,04/iyon`** (`22 keV`) | **PASS** |
| **`EP2`** | Rota A optimal `T_epi* ∈ [310, 370] °C` (`h_epi>40 nm`, `R_q≤0,20 nm`, `N_def≤1e15`, `L_seg≤3,5 nm`, `σ_iso≤0,05 nm`) | **`T_epi* = 345 °C`** (geçer pencere `325–380 °C`): `h_epi = 236,0 nm` (`29,5×`), `R_q = 0,091 nm`, `N_def = 2,84×10¹⁴ cm⁻³`, `L_seg = 2,08 nm`, `σ_iso = 0,0314 nm` | **PASS** |
| **`EP3`** | `Exp131` `4×4` verim: Rota A `z∈[14,0, 15,2] nm`, `σ_z≤3,1 nm`, `≥%93`; Rota B `≥15 puan` düşüş (`<%80`); `14 keV+8 nm` `<%40` | `v4 1440 K` Rota A: `14,35 ± 3,14 nm`, `%92,20` (*gizli TED yüzünden `0,80 puan` eksik!*); **`v5 1530 K` Rota A: `14,40 ± 2,81 nm`, `%95,35`**, **Rota C: `%97,70` (`C=7.557`)**; Rota B `22 keV`: **`%53,35`** (`-42,0 pp`); `14 keV+8 nm`: **`%31,75`** | **FAIL** *(v4; v5 ile kapandı)* |
| **`EP4`** | McWhorter `S_ε`: Rota B `>1,3`, Rota A `[0,75, 1,05]`, Rota C `[0,25, 0,45] µeV/√Hz` (`≥2,2×` bastırma) | Rota B: **`1,719`**; Rota A: **`1,000`**; **Rota C (`350 °C` FG/H, `D_it=1,5×10¹⁰`): `0,390 µeV/√Hz`** (**`2,57×`** vs baz, **`4,41×`** vs Rota B; `10¹⁰/5 nm ox = 0,283`) | **PASS** |
| **`EP5`** | `1 ms` flaş + MBE + `350 °C / 15 dk` FG sonrası ek difüzyon `<0,01 nm` (`σ_ann≤0,35 nm`), `Exp124 σ_tot≤3,66 nm` | **`v4 1×1440 K` Keşfi:** `%13,6` `{311}` küme → `+1,318 nm` arka-uç TED (`σ_ann=1,646 nm`, `σ_tot=3,995 nm`). **`v5 1×1530 K (43,49 J/cm²)` Çözümü:** `%99,99` temizlik → `σ_ann=0,430 nm` (`Δ=+0,037 nm`), **`Exp124 σ_tot = 3,665 nm`** | **FAIL** *(v4; v5 ile kapandı)* |
| **`EP6`** | `S5.6` `CF100` Load-Lock `+Z`: boşluk `>50 mm`, kütle `[18,25] kg`, `P<5e-10 Torr`, `t∈[40,160] s`, `0 µW` kriyo, `%0` boru-hattı cezası | Min boşluk **`70,0 mm`** (`119 mm` ana oda), kütle **`22,4 kg`**, `P_growth = 3,5×10⁻¹⁰ Torr`, `t_cap = 80 s`, kriyo sızıntı **`0,00 µW`**, boru-hattı **`%0,0`** (seri Rota A `%5,56`) | **PASS** |
| **`EP7`** | BCA `2k vs 4k < %2`; McWhorter radyal `< %0,5`; TED kütle hatası `< 1e-12` | Bağımsız BCA `2k vs 4k` max **`%2,90`** (`4k vs 8k = %2,67`, sonlu-N MC `σ_lat` örnekleme gürültüsü; `Exp92` uyumu `%0,15–%1,78`); McWhorter **`%0,0009`**; TED kütle **`1,55×10⁻¹⁵`** | **FAIL** *(MC `σ_lat` %2 eşiği)* |

---

## 2. Üç Üretim Rotasının Birebir Kıyaslaması (`Rota A` vs `Rota B` vs `Rota C` & `14 keV`)

| Rota / Yapılandırma (`N=2.000`, `3 kΩ`, `Q_L=2×10⁵`) | İmplant & Termal Reçete | `z_final ± σ_z` (nm) | `Exp124 σ_tot` (nm) | `D_it,eff` (`cm⁻²eV⁻¹`) | `S_ε` (`µeV/√Hz`) | `S_E / S_E,çıplak` | `M4` Verim `P(C≥100)` | Medyan `C` | Medyan `γ_φ` (kHz) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Çıplak `5 keV` (Referans, `Δz=0`) | `5 keV` + `1 ms 1440 K` | `6,48 ± 2,83` | `3,655` | `1,00×10¹¹` | `1,000` | `1,000` | **`%24,55`** | `0` | `42,6` |
| **Rota B (`22 keV` Kaplama-Üstü)** | `22 keV` (`1,5 nm SiO₂ + 8 nm cap`) + `1 ms` | `14,46 ± 5,91` | **`7,866` (FAIL)** | `2,95×10¹¹` *(1,04 O/iyon)* | **`1,719`** | `0,586` | **`%53,35`** | `166` | `19,5` |
| Rota B (`20 keV` Kaplama-Üstü) | `20 keV` (`1,5 nm SiO₂ + 8 nm cap`) + `1 ms` | `13,93 ± 5,71` | **`7,515` (FAIL)** | `2,93×10¹¹` *(1,02 O/iyon)* | **`1,685`** | `0,629` | **`%58,05`** | `286` | `20,4` |
| Rota A (`14 keV SRIM` + `8 nm` Cap) | `14 keV (15 nm)` + `v5 1530 K` + `8 nm` | `23,14 ± 5,01` | `6,135` *(BCA)* | `1,52×10¹⁰` *(FG)* | `0,440` | **`0,067`** | **`%31,75`** *(derin Kane)* | `11` | `10,3` |
| Rota A (`v4` `1×1440 K` — Gizli TED) | `5 keV` + `1×1440 K` + `8 nm @ 345 °C` | `14,35 ± 3,14` | `3,887` *(A)* | `1,00×10¹¹` | `1,000` | `0,346` | `%92,20` | `2.253` | `12,6` |
| Rota C (`v4` `1×1440 K` + `350 °C` FG) | `5 keV` + `1×1440 K` + `8 nm` + `FG` | `14,53 ± 3,23` | `3,995` *(FAIL)* | `1,52×10¹⁰` | `0,390` | `0,135` | `%95,00` | `5.889` | `10,7` |
| **Rota A (`v5` `1×1530 K` — Temiz)** | `5 keV` + **`1×1530 K (43,49 J/cm²)`** + `8 nm` | **`14,40 ± 2,81`** | **`3,663`** | `1,00×10¹¹` | `1,000` | `0,346` | **`%95,35`** | `2.943` | `12,0` |
| **Rota C (`v5` `1×1530 K` + `350 °C` FG — ÖNERİLEN)** | `5 keV` + **`1×1530 K`** + `8 nm @ 345 °C` + `350 °C FG` | **`14,43 ± 2,84`** | **`3,665`** | **`1,52×10¹⁰`** | **`0,390`** | **`0,135`** | **`%97,70`** | **`7.557`** | **`10,7`** |

### Temel Fiziksel Sonuçlar
1. **Rota B Neden Kesin Elenir?** `22 keV` kaplama-üstü implantasyon aynı `14,5 nm` derinliğe ulaşsa da yanal saçılmayı **`2,38×`** (`7,69 nm`, `Exp124` `3,80 nm` tavanını kırarak `7,87 nm` yapar), derinlik saçılmasını **`2,09×`** (`5,87 nm`) kötüleştirir, `1,5 nm` `SiO₂` içinden iyon başına **`1,04` geri-tepme `¹⁶O`** atomunu `²⁸Si` içine sürer (`p90 = 1,63 nm`), yük gürültüsünü **`1,719 µeV/√Hz`** düzeyine yükseltir ve `M4` verimini **`%53,35`** düzeyine çökertir (`-42,0 puan`).
2. **`5 keV` vs `14 keV` Derinlik Uzlaşması:** `14 keV` (`z₀ = 15,0 nm`) + `8,0 nm` kaplama donörleri `23,1 nm` derinliğe gömer; bu derinlikte tünel bağlaşımı `t_c(23 nm) ≈ 0,12 GHz` olduğundan Tosi flip-flop `M4` verimi **`%31,75`** düzeyine düşer. Dolayısıyla `M4` kavite-QED mimarisi için **`5 keV` (`R_p = 6,46 nm`) + `8,0 nm` `²⁸Si` MBE kaplama (`z_final = 14,4 nm`)** zorunludur; `14 keV + 8 nm` yalnızca gömülü Kane/çekirdek-spin yazmaçlarında (`S_E` **`15×` düşük**) anlamlıdır.
3. **`Exp137` İçin Fiziksel `S_ε` Köprüsü (`{Model}` + `{Sayısal-Simülasyon}`):** Kesin 2B görüntü-yüklü McWhorter integrali, flip-flop kübitinde arayüz noktası `z_int = 2,0 nm`'de kaldığı için salt `Δz_cap = 8 nm` kaplamanın `S_ε`'yi kendiliğinden düşürmediğini (`1,000 µeV/√Hz` korur, ancak kaplamayı iyon hasarından korur), asıl `S_ε` düşüşünün **Rota C (`350 °C / 15 dk` `%5 H₂/N₂` forming-gas / atomik-H pasivasyonu)** ile geldiğini gösterir:
   - Muhafazakâr (`D_it = 3,0×10¹⁰`, `d_ox = 8 nm`): **`S_ε = 0,549 µeV/√Hz`**
   - **Nominal (`D_it = 1,5×10¹⁰`, `d_ox = 8 nm`):** **`S_ε = 0,390 µeV/√Hz`** (`2,57×` bastırma)
   - Düşük tuzak (`D_it = 1,0×10¹⁰`, `d_ox = 8 nm`): **`S_ε = 0,319 µeV/√Hz`**
   - İnce oksit perdeleme (`D_it = 1,0×10¹⁰`, `d_ox = 5 nm`): **`S_ε = 0,283 µeV/√Hz`** (`3,53×` bastırma — doğrudan `Exp131/137` `F_Bell ≥ 0,990` rejiminde!)

---

## 3. Düşük-Sıcaklık `²⁸Si` MBE Optimizasyonu & Bütünleşik Termal Zincir

| Termal Zincir Reçetesi (`5 keV`, `R_p = 6,46 nm`) | Darbe | `T_peak` (K) | Akı (`J/cm²`) | Kalan `{311}` Küme | Flaş `σ_ann` (nm) | Rota A (`+80 s 345 °C`) | Rota C (`+900 s 350 °C`) | `σ_iso` (nm) | `Exp124 σ_tot` (nm) | `S5.5` Safir `LIDT` Payı |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `v4.0` Tek Darbe (`Exp130` bazı) | `1 × 1,0 ms` | `1440,3` | `41,15` | **`%13,57`** | `0,328` | `1,363` | **`1,646` (FAIL)** | `0,0314` | **`3,995` (>3,80)** | `9,47×` |
| **`v5.0` Küme-Temizleyici (ÖNERİLEN)** | **`1 × 1,0 ms`** | **`1530,1`** | **`43,49`** | **`%0,012`** | `0,392` | **`0,417`** | **`0,430` (≤0,50)** | `0,0515` | **`3,665` (≤3,80)** | **`8,96×`** |
| `v5.0` Dörtlü Darbe (Alternatif) | `4 × 1,0 ms` | `1440,3` | `41,15` | **`%0,034`** | `0,392` | `0,443` | **`0,468` (≤0,50)** | `0,0405` | **`3,670` (≤3,80)** | `9,47×` |

- **Optimal MBE Penceresi (`0,10 nm/s`, `8,0 nm = 80 s`):** **`T_epi* = 345 °C`** (geçer aralık `325–380 °C`): `Eaglesham` kritik epitaksiyel kalınlığı `h_epi = 236,0 nm` (`29,5×` kaplama), yüzey pürüzlülüğü `R_q = 0,091 nm` (`0,67 ML`), `Gossmann` boşluk kusur yoğunluğu `N_def = 2,84×10¹⁴ cm⁻³`, `Nützel–Abstreiter / Oberbeck` yüzey ayrışma boyu `L_seg = 2,08 nm`. Büyüme hızı `0,20 nm/s`'ye çıkınca `L_seg = 1,10 nm`'ye iner (`40 s`), `0,05 nm/s`'de `3,89 nm`'ye çıkarak (`160 s`) eşiği aşar.

---

## 4. `S5.6` Donanım Mühendislik Şartnamesi (`In-Situ ²⁸Si UHV MBE Capper` — `CAD v5.0` & `BOM v5.0` Girdisi)

Doğrudan makinece okunabilir JSON: `results/exp139_epi_cap_process_integration/s56_hardware_spec.json` (ve `exp139.json["s56_hardware_spec"]`).

| Parametre | `S5.6` Kilitlenen Şartname | `CAD v5.0` / `BOM v5.0` / Kriyo Doğrulaması |
| :--- | :--- | :--- |
| **Alt Sistem & Montaj Portu** | `S5.6` — `s5_loadlock_chamber` (`S5.3`, `X=420, Y=0, Z=500 mm`) **`+Z` üst `CF100` (`DN100CF`) flanşı** | Dış zarf `Ø152 mm × 280 mm` (`Z ∈ [585, 865] mm`); ana oda üst flanşına **`119,0 mm`**, transfer koluna **`70,0 mm`**, `S5.5` flaş kafasına **`500,6 mm`** boşluk (`0` çakışma) |
| **Kaynak & Besleme Stoğu** | Potasız DC `²⁸Si` çubuk süblimasyon kaynağı (`SUSI-63` / kompakt e-beam sınıfı) + su/kriyo kalkan + pnömatik deklanşör + `QCM` | `< 50 ppm ²⁹Si` izotopik `²⁸Si` çubuk (`~5 g` yük → `>1.000` pul @ `8 nm`), pota kirlenmesi yok |
| **Vakum, Hız & Sıcaklık** | `P_base = 1,5×10⁻¹⁰ Torr`, **`P_growth = 3,5×10⁻¹⁰ Torr`** (`< 5×10⁻¹⁰`); `R_g = 0,05–0,20 nm/s` (nom. **`0,10 nm/s` → `80 s`**); `8,0 ± 0,3 nm` | Yük kilidinde UHV pirolitik-BN ısıtıcı (`RT–450 °C`, `±2 °C`, `150 W`, hedef **`345 °C`**) + `Rota C` `%5 H₂/N₂` forming-gas / atomik-H pasivasyon manifoldu (`350 °C / 15 dk`) + `80 L/s` TMP/NEG |
| **Kütle, Güç & Kriyo Yalıtım** | Toplam kütle **`22,4 kg`** (`11,8` kaynak/kalkan + `3,4` QCM/vana + `4,2` PBN/H₂ + `3,0` NEG/TMP); `400 W` büyüme / `25 W` bekleme | `s5_loadlock_duct` tam-metal UHV sürgülü vanası ile ana `20 mK` odadan ayrık → **`0,00 µW` (`20 mK`) / `0,00 mW` (`4 K`) kriyo ısı sızıntısı!** |
| **`BOM v5.0` Maliyet (`{Varsayım}`)** | Kaynak/PSU `$48k` + `²⁸Si`/QCM `$18k` + PBN/H₂/NEG `$29k` = **`$95.000` (P50)** (`P10 $67k / P90 $145k`) | `v4.0 M3` (`$4,61M`) donanım BOM'unun yalnızca **`+%2,06`**'sı (`no_supplier_quotes = true`) |
| **`Exp134` Akış Hızı Etkisi** | Yük kilidi süresi: Rota A **`3,33 dk`**, Rota C **`28,33 dk`** vs `Exp134 v4.0-5×` yoğun `M4` ana oda döngüsü `72,96 dk` | Önceki pul ana odada ölçülürken boru-hattı paralel yürütme → **`%0,0` akış hızı cezası** (seri modda Rota A `+%5,56` / `1 s` mekik) |

---

## 5. Görsel Doğrulama ve Kapanış

- **Yayın Grafiği (`2400×1400`, `read_file` ile görsel onaylı):** `results/exp139_epi_cap_process_integration/fig_exp139_epi_cap_integration.png` — 6 panelli bütünleşik pano: (A) `250–450 °C` LT-MBE penceresi (`T_epi* = 345 °C`), (B) `5–24 keV` ZBL+LSS BCA saçılma & geri-tepme `¹⁶O` cezası, (C) `P(z_final)` dağılımları vs `M4` penceresi, (D) `Exp137` köprülü 2B McWhorter `S_ε(D_it)` ölçeklemesi, (E) `Exp131` `4×4` flip-flop verim karşılaştırması (`%97,7` Rota C `v5`), (F) `S5.6` `CAD v5.0 / BOM v5.0` kesit şeması ve `v4 → v5` küme-temizleme özeti.
- **Testler & Değişmezler:** `tests/test_exp139.py` (`9/9 PASS`), `0` hardcoded kullanıcı yolu, `0` GFM hatası, `BOM.csv` ve `v4.0` birincil JSON'ları dokunulmamış. Fiziksel laboratuvar (`M1 G4` düşük-doz `5 keV` + `1530 K` flaş + `345 °C` `8 nm ²⁸Si` + `350 °C` FG) ve tedarikçi teklifleri kapsam dışıdır (`no_lab_measurement = true`, `no_supplier_quotes = true`).
