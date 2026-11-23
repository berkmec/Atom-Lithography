# Exp140 (H158) — Gerçek-Zamanlı `Q16.16` BOED-FPGA Hızlandırıcısı, `3 kΩ` `NbTiN` Frekans-Çoklamalı Kriyo Okuma ve `CellISA v3.5` Raporu

- **Deney / Hipotez:** `exp140_cryo_fpga_boed_mux_readout` / `H158`
- **Tarih:** 2026-11-23
- **Epistemik Etiket:** `{Model}` / `{Sayısal-Simülasyon}` / `{Liste-Çapası}` — **`no_lab_measurement = true`**, **`no_supplier_quotes = true`**
- **Genel Karar:** **7/7 Ön-Kayıtlı Tahmin `PASS`** (`success_rule_met = true`, çalışma süresi `3,75 s`)

---

## 1. Yönetici Özeti

`Exp132` kapalı döngü BOED spektroskopisini Python `FP64`'te `24,4×` hızlandırmış, `Exp131` ise `3 kΩ` `NbTiN` yüksek-empedanslı kavite-QED rezonatörlerini tanımlamıştı. **Exp140 (`H158`)**, bu kontrol ve okuma katmanını dört gerçekçi donanım ve mimari sütunda kapatmıştır:

1. **Bit-Doğru `Q16.16` BOED-FPGA DSP Motoru (`src/machine_control/fpga_boed_dsp.py`):**
   - `250 MHz` `Xilinx ZU48DR RFSoC` üzerinde `4` paralel SIMD hattı, `512`-girdili doğrusal-ara-değerlemeli BRAM36 Lorentzian ve `exp(-x)` tabloları ile `48`-bit `DSP48E2` moment toplayıcıları kullanır.
   - `N = 400` eşleştirilmiş `Exp132` adayı (`1.712` hiperince çizgisi) üzerinde `FP64` vs `Q16.16`: **`RMS = 73,38 Hz` vs `73,33 Hz`** (**`|ΔRMS| = 0,0502 Hz << 1,0 Hz`**), `ΔFNR = %0,0000`, `ΔFPR = %0,0000`, `0` Stage-0 SPRT ayrışması.
   - Döngü-kesin adım gecikmesi: **`584` saat çevrimi = `2,336 µs`** (`< 25 µs` hedefine `10,7×` marj); `16` paralel BOED motoru tek `ZU48DR`'de **`%10,49` DSP48E2, `%5,93` BRAM36, `%15,80` LUT** ve `37,98 W` oda-sıcaklığı gücü (`0 W` kriyo yük) tüketir.

2. **`3 kΩ` `NbTiN` Frekans-Çoklamalı (`4,0–8,0 GHz`) + Purcell + `20 mK` TWPA + `4 K` HEMT Okuma Zinciri:**
   - Ortak bant-geçiren Purcell filtresi (`κ_p/2π = 80 MHz`, `Δ_q/2π = 1,0 GHz`) **`625,0×` Purcell koruması** (`T_1,Purcell = 124,34 ms` vs filtresiz `198,9 µs`) sağlar.
   - `20 mK` TWPA (`T_N = 0,30 K`, `G = 20 dB`, `P_1dB = -98 dBm`) + `4 K` HEMT (`T_N = 2,0 K`) kaskadı sistem gürültüsünü `4,681 K`'den **`0,6719 K`**'ye düşürür (`η_meas = %21,43`).
   - TWPA `P_1dB = -98 dBm` doyması/IM3 geri çekilmesi ve yüksek-Z `NbTiN` kinetik-endüktans saçılması (`σ_fab = 15 MHz`) fiziksel tavanı **`N_mux* = 32` rezonatör/hat** olarak kilitler (`F_RO(2 µs) = 0,9961`, `100 MHz` aralık, `%0,0009` çarpışma); **`N_mux = 64`** ise `5,34 dB` TWPA geri çekilmesi ve `%3,81` kanal çarpışması nedeniyle **`0,9413`**'e çökerek `%99` sınırının altında kalır!

3. **`1.024` vs `10.000` Hücreli `M4` Dizileri İçin Dürüst 4-Kademeli Kriyostat Isı Yükü Bütçesi (`Exp125` Çapalı):**
   - **`1.024` hücre (`32` RO + `32` XY = `96` koaksiyel):** Tek `Bluefors LD400 / PT420` içinde **4 kademenin TAMAMI kapanır** (`20 mK = 6,26 / 14 µW`, `100 mK = 59,6 / 400 µW`, `4 K = 0,488 / 2,0 W`, `50 K = 8,26 / 40 W`).
   - **`10.000` hücre (`313` RO + `313` XY = `939` koaksiyel):** Tek `PT420`/`LD400` **4 kademede de DÜRÜSTÇE AŞILIR** (`20 mK = 43,63 µW [3,12×]`, `100 mK = 451,0 µW [1,13×]`, `4 K = 3,938 W [1,97×]`, `50 K = 58,84 W [1,47×]`). Tek kriyostatın fiziksel tavanı **`2.887` hücredir** (`#1` darboğaz `20 mK MXC`); `10.000` hücre için **`>= 4` modüler `LD400/PT420`** (veya `XLD1000/KIDE` çoklu-`PT420` + `2,1 mW` düşük-güçlü HEMT) şarttır!

4. **`CellISA v3.5` (`17` Komut) & `S6.5` Donanım Şartnamesi (`CAD/BOM v5.0` İçin):**
   - `ECHO_CZ`, `MUX_READOUT`, `SYNDROME_CYCLE` komutları eklendi (`v2.0/v3.0` ile `%100` geriye dönük uyumlu). Canlı `4×4` yonga sendrom çevriminde `1/f` yük gürültüsü (`S_ε = 1,0 µeV/√Hz`) altında `Bare CZ = 0,7791` → **`ECHO_CZ = 0,9818` (`+20,27` puan kazanım)**, çevrim sadakati **`0,9427`** (`T_cyc = 2,620 µs`), `SHA-256` imzalı `MultiCellCertificate(isa_version="3.5")`.
   - `S6.5` `1.024`-hücreli modül donanım paketi: toplam kütle **`19,27 kg`** (`7,77 kg` soğuk kütle), oda gücü `87,96 W`, nominal tahmin **`$629.200`** (`$456,4k–$925,2k`).

---

## 2. Ön-Kayıtlı Karar Tablosu (`predictions_exp140.json` → `7/7 PASS`)

| Tahmin ID | Ön-Kayıtlı Kriter | Ölçülen Sonuç (`exp140.json`) | Karar |
| :--- | :--- | :--- | :---: |
| `FM1_Q16_16_FP64_PARITY` | `abs(ΔRMS) < 1,0 Hz`, `abs(ΔFNR) < %0,05`, `RMS_Q16 <= 100 Hz` | `abs(ΔRMS) = 0,0502 Hz`, `ΔFNR = %0,0000`, `RMS_Q16 = 73,38 Hz`, `0` SPRT farkı | **PASS** |
| `FM2_FPGA_CYCLE_LATENCY_AND_RESOURCES` | Adım gecikmesi `< 25 µs`, `16` ch `< %25` `ZU48DR` kaynağı | `584` cyc = **`2,336 µs`**, DSP `%10,49`, BRAM `%5,93`, LUT `%15,80` | **PASS** |
| `FM3_PURCELL_AND_TWPA_SINGLE_SHOT_RO` | Purcell `> 100×`, `T_1,P > 10 ms`, `F_RO(32, 2 µs) >= 0,990` | Purcell **`625,0×`**, `T_1,P = 124,34 ms`, `F_RO(32, 2 µs) = 0,9961` | **PASS** |
| `FM4_PHYSICAL_NMUX_CEILING` | `N_mux = 64` `< 0,990` düşüşü, fiziksel optimum `N_mux* ∈ {16, 32}` | **`N_mux* = 32`** (`0,9961`), `N_mux = 64` → **`0,9413`** (`5,34 dB` BO, `%3,81` çarpışma) | **PASS** |
| `FM5_CRYO_BUDGET_1024_CLOSES_10000_WALL` | `1.024` 4 kademede kapanır; `10.000` tek `PT420`'yi aşar (`>= 4` kriyostat) | `1.024`: `PASS` (`6,26 µW / 0,488 W`); `10.000`: **`43,6 µW / 3,94 W` → `4` kriyostat** | **PASS** |
| `FM6_CELLISA_V35_SYNDROME_AND_BACKCOMPAT` | `17` komut, `ECHO_CZ` kazanımı, `SHA-256` `v3.5` sertifikası | `17` komut, `0,7791 → 0,9818` (`+0,2027`), `F_syn = 0,9427`, `SHA-256 = True` | **PASS** |
| `FM7_S65_SPEC_PORTABILITY_AND_TESTS` | `S6.5` JSON, `0` hardcoded yol, `0` GFM hatası, tüm pytest `PASS` | `s65_hardware_spec.json` hazır, `0` yol ihlali, `0` GFM hatası, `7/7 + 142/142 PASS` *(tarihsel `v4.0` paketi; güncel `v5.0`: `198/198`)* | **PASS** |

---

## 3. Frekans-Çoklama (`4–8 GHz`) ve Kriyostat Isı Yükü Tabloları

### 3.1 `N_mux` Taraması (`3 kΩ NbTiN`, `τ_RO = 2,0 µs`, `P_1dB = -98 dBm`, `σ_fab = 15 MHz`)

| `N_mux` | Kanal Aralığı (`MHz`) | `P_peak` TWPA (`dBm`) | TWPA Geri Çekilme (`dB`) | Etkin `n_bar` | Çarpışma Olasılığı | `F_RO (2,0 µs)` | En İyi `F_RO` | Karar |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `8` | `400,0` | `-106,58` | `0,00` | `40,0` | `%0,0000` | `0,9982` | `0,9982 @ 2 µs` | PASS |
| `16` | `200,0` | `-102,61` | `0,00` | `40,0` | `%0,0000` | `0,9982` | `0,9982 @ 2 µs` | PASS |
| **`32`** | **`100,0`** | **`-98,64`** | **`1,36`** | **`29,2`** | **`%0,0009`** | **`0,9961`** | **`0,9978 @ 3 µs`** | **`N_mux*` KİLİTLİ** |
| `64` | `50,0` | `-94,66` | `5,34` | `11,7` | `%3,8063` | `0,9413` | `0,9754 @ 5 µs` | **DUVAR (FAIL)** |

### 3.2 `1.024` vs `10.000` Hücreli `M4` Kriyostat Isı Yükü (`N_mux* = 32`, `XY_mux = 32`)

| Dizi Ölçeği & HEMT | RO + XY Koaksiyel | `20 mK MXC` (`<= 14 µW`) | `100 mK CP` (`<= 400 µW`) | `4 K PT420` (`<= 2,0 W`) | `50 K` (`<= 40 W`) | Tek `LD400/PT420` | Gerekli Kriyostat |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`1.024` hücre (`7,8 mW` HEMT)** | `96` hat | **`6,256 µW`** (`%44,7`) | **`59,58 µW`** (`%14,9`) | **`0,4880 W`** (`%24,4`) | **`8,26 W`** (`%20,7`) | **KAPANIR (`PASS`)** | `1` |
| `1.024` hücre (`2,1 mW` HEMT) | `96` hat | `6,256 µW` (`%44,7`) | `59,58 µW` (`%14,9`) | `0,3056 W` (`%15,3`) | `8,26 W` (`%20,7`) | **KAPANIR (`PASS`)** | `1` |
| **`10.000` hücre (`7,8 mW` HEMT)** | `939` hat | **`43,629 µW`** (`%311,6`!) | **`451,01 µW`** (`%112,8`!) | **`3,9384 W`** (`%196,9`!) | **`58,84 W`** (`%147,1`!) | **AŞILIR (`FAIL`)** | **`4` (`<= 2.887`/ünite)** |
| `10.000` hücre (`2,1 mW` HEMT) | `939` hat | `43,629 µW` (`%311,6`!) | `451,01 µW` (`%112,8`!) | `2,1543 W` (`%107,7`!) | `58,84 W` (`%147,1`!) | **AŞILIR (`FAIL`)** | **`4` (`20 mK` sınır)** |

---

## 4. `S6.5` Donanım Mühendislik Şartnamesi (`CAD v5.0` & `BOM v5.0` Girdisi — `1.024` Hücreli Modül)

Ayrıntılı makine-okunur JSON: `results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json` (`no_supplier_quotes = true`, `{Liste-Çapası}`/`{Varsayım}`):

| Parça ID | Bileşen | Adet | Kademe | Zarf (`mm`) | Kütle (`kg`) | Güç / Kriyo Yük | Maliyet Bandı (`USD`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `S6.5-01` | `ZU48DR RFSoC` `Q16.16` BOED-FPGA `2U` Kasa (`32` ch) | `1` | `300 K` Raf | `482,6×520×88,9` | `11,50` | `87,96 W` (`0 W` kriyo) | `$58.000` (`$42k–$82k`) |
| `S6.5-02` | `20 mK` Josephson TWPA + Purcell Filtre + Çift İzolatör | `32` | `20 mK MXC` | `180×140×55` | `2,72` | `2,14 µW @ 20 mK` | `$336.000` (`$240k–$512k`) |
| `S6.5-03` | `4 K` `LNF-LNC4_8C` Sınıfı HEMT Bankası (`7,8 mW`) | `32` | `4 K` Flanş | `220×120×40` | `1,02` | `0,2496 W @ 4 K` | `$144.000` (`$112k–$192k`) |
| `S6.5-04` | Kriyo-Koaksiyel Demet (`CuNi/NbTi 0,86 mm`, `96` hat) | `96` | `300K→20mK` | `95×95×620` | `4,03` | `5,76 W @ 50 K` | `$91.200` (`$62,4k–$139,2k`) |
| **Toplam** | **`S6.5` `1.024`-Hücreli `M4` Okuma-Kontrol Modülü** | — | — | — | **`19,27 kg`** (`7,77` soğuk) | **`87,96 W` @ `300 K`** | **`$629.200`** (`$456,4k–$925,2k`) |

---

## 5. Kapsam Dışı / Varsayımlar (Epistemik Kalibrasyon)

- `no_lab_measurement = true` & `no_supplier_quotes = true`: `ZU48DR` kaynak bütçesi Xilinx `DS926` kapasitelerine, TWPA/HEMT/Purcell zinciri analitik kavite-QED + Friis modeline, `S6.5` maliyetleri liste çapası ve mühendislik varsayımlarına dayanır.
- `Q16.16` motoru Python `int64` üzerinde bit-doğru donanım aritmetiği ve döngü-kesin zamanlama modeli olarak doğrulanmıştır; Vivado/HLS Verilog sentezi ve fiziksel FPGA üzerinde zamanlama kapanışı henüz yapılmamıştır.
- `CellISA v3.5` `ECHO_CZ` modeli `4×4` Kraus `1/f` filtre-fonksiyonu temsilidir; tam `12×12` / `24×24` renkli `1/f^α` Ornstein–Uhlenbeck Lindblad yörünge kapanışı paralel `Exp137` görevi kapsamındadır.
