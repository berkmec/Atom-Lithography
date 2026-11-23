# Exp132 (H150) — Kapalı Döngü Bayesyen Uyarlamalı Spektroskopi (BOED) ve CellISA v3.0 Çoklu-Hücre (M4) Derleyici Raporu

- **Deney / Hipotez:** `exp132_bayesian_spectroscopy_cellisa3` / `H150`
- **Tarih:** 2026-11-23
- **Epistemik Etiket:** `{Model}` / `{Sayısal-Simülasyon}` — **`no_lab_measurement = true`**
- **Genel Karar:** **6/6 Ön-Kayıtlı Tahmin `PASS`** (`success_rule_met = true`, çalışma süresi `34.35 s`)
- **Ek Donanım Maliyeti:** **`$0`** (yalnızca AWG/FPGA yazılım kontrol döngüsü; mevcut 56 RF zinciri × `N_L = 160` = `8,960` okuma kanalı korunmuştur)

---

## 1. Yönetici Özeti

`DESIGN.md v3.0` (kilitli `Arch-B`: `1,024` ışın demeti @ `15 ms` atış döngüsü, `%50` görev döngüsü, `5 keV` `P91`, `Cold-100K` IBIC `η = 0.9994`) altında yazma katmanı günde `1.503 × 10⁹` sertifikalı yazmaç kapasitesine ulaşabilirken, sabit `1.0 s/aday` spektroskopi taraması fabrikayı günde **`1.973 × 10⁸` yazmaç** seviyesinde okuma-sınırlı (readout-limited) kilitliyordu.

**Exp132 (`H150`)** bu darboğazı `$0` ek donanımla iki katmanda çözmüştür:

1. **3 Aşamalı Kapalı Döngü BOED Spektrometre (`src/machine_control/adaptive_spectroscopy.py`):**
   - `Exp125` 20 mK RF-Elzerman SNR çapasına (`1.4 K` LNA, `-100 dBm/ton`, `Q_L = 1000`, `|ΔΓ| = 0.05` → `τ_SNR10 = 0.062705 ms`) kilitli olarak `N = 2,000` Mode B (`f = %1`) adayı üzerinde ortalama spektroskopi süresini `1,000.0 ms`'den **`41.03 ms`**'ye düşürmüştür (**`24.37×` ham okuma hızlanması**, medyan `23.04 ms`).
   - **Erken İptal (Early-Abort):** Boş (`blank`) yuvalar **`0.73 ms`**'de (Stage 0 ESR-SPRT), kalabalık (`crowded`, `< 5 kHz` çarpışma) adaylar **`14.58 ms`**'de (Stage 1 10-tonlu tarak + yerel vadi/ikili-tepe LLR) reddedilmiştir.
   - **Frekans Keskinliği ve Sınıflandırma:** Çalışan adayların `7,952` hiperince çizgisi üzerinde Stage 2 Fisher-optimal büküm noktası (`f̂ ± γ/√3`) güncellemesi ampirik **`RMS = 72.67 Hz`** (`CRLB = 58.19 Hz`, eski `200 Hz` sabit taramaya göre **`2.75×` daha keskin**), **`FNR = %0.20`** (`2/996`) ve **`FPR = %0.00`** (`0/1,004`) vermiştir.
   - **Fabrika Verimi ve Yazma Tavanı Geçişi:** `v4.0` BOED okuma kapasitesi günde `4.810 × 10⁹` yazmaca fırlayarak `131.33 ms` (`7.61×`) geçiş eşiğinin çok altına inmiştir. Böylece kilitli `Arch-B` (`1,024 @ 15 ms`) tam **`1.503 × 10⁹` sertifikalı yazmaç/gün (`7.61×` gerçekleşen fabrika hızlanması — YAZMA-SINIRLI)** tavanına, `10 ms` ışın döngüsü yükseltmesinde ise **`2.254 × 10⁹` yazmaç/gün (`11.42×`)** tavanına ulaşır.

2. **`CellISA v3.0` Çoklu-Hücre (`M4`) Derleyici ve Heterojen Wafer Yönlendirici (`src/machine_control/programmer.py`):**
   - `CellISA v2.0` ile `%100` geriye dönük uyumlu olarak 4 yeni komut eklenmiştir: `WAFER_MAP_ROUTE`, `BUS_TUNE`, `BUS_CZ`, `LOGICAL_ENCODE`.
   - `N = 200` heterojen `%51` verimli `4×4` wafer Monte Carlo taramasında `4`-hücreli `M4` mantıksal küme yönlendirilebilirliği **`%97.0`** (ortalama `1.009` bus atlaması), `6`-hücreli küme yönlendirilebilirliği **`%89.0`** ölçülmüştür.
   - Örnek `4×4` wafer üzerinde (`10` çalışan / `6` ölü yuva baypas) yüksek-empedanslı `NbTiN` dispersif kavite-QED veri yolu (`g = 15 MHz`, `Δ = 150 MHz`, `κ = 0.50 MHz`, `J_bus = 1.50 MHz`, `t_CZ = 0.1667 µs`) + tam `4×4` Kraus Purcell/$T_2$ kanalı + yerel hücre-özgü nükleer RF `CNOT(e, n0)` derlemesi **`min_bus_cz_fidelity = 0.988923`**, **`joint_state_fidelity = 0.983448`**, `3`-hücre tekrarlama kodu mantıksal hata baskılaması **`p_L = 3.65 × 10⁻⁴` (`30.3×` hata azalması)** ve doğrulanmış `SHA-256` `MultiCellCertificate` + taşınabilir `Exp126` `32D` köprüsü üretmiştir.

---

## 2. Ön-Kayıtlı Tahminler ve Karar Tablosu (`predictions_exp132.json`)

Ön-kayıt dosyası `results/exp132_bayesian_spectroscopy_cellisa3/predictions_exp132.json` simülasyon çalıştırılmadan önce dondurulmuş ve `run_exp132.py` ile doğrulanmıştır:

| Tahmin ID | Ön-Kayıtlı Kriter | Ölçülen Değer (`exp132.json`) | Epistemik Etiket | Karar |
| :--- | :--- | :--- | :--- | :--- |
| `DA1_EARLY_ABORT_LATENCY` | `blank < 3.0 ms`, `crowded < 15.0 ms` | `blank = 0.73 ms`, `crowded = 14.58 ms` | `{Sayısal-Simülasyon}` | **PASS** |
| `DA2_PRECISION_SIGMA_100HZ` | Çalışan çizgi RMS hatası `<= 100.0 Hz` | `RMS = 72.67 Hz` (`MAE = 57.43 Hz`, `CRLB = 58.19 Hz`) | `{Sayısal-Simülasyon}` | **PASS** |
| `DA3_CLASSIFICATION_INTEGRITY` | `N = 2,000` içinde `FNR < 1.0%`, `FPR < 0.5%` | `FNR = 0.20%` (`2/996`), `FPR = 0.00%` (`0/1,004`) | `{Sayısal-Simülasyon}` | **PASS** |
| `DA4_SPEEDUP_AND_WRITE_CEILING` | `t_spec < 150 ms`, `>= 1.0 × 10⁹` yazmaç/gün | `t_spec = 41.03 ms` (`24.37×` ham), `1.503 × 10⁹/gün` (`7.61×` yazma tavanı) | `{Model}` | **PASS** |
| `DA5_CELLISA3_MULTICELL_ROUTING` | `4×4` 4-hücre yönlendirme `>= 90%`, `F_CZ >= 0.94`, `SHA-256` + `Exp126` | `%97.0` (`N=200`), `F_CZ = 0.9889`, `F_joint = 0.9834`, `SHA-256 = True` | `{Model}` | **PASS** |
| `DA6_PORTABILITY_AND_TESTS` | `%100` pytest geçişi ve sıfır sabitlenmiş konak yolu | `41/41 pytest PASS`, `portability_hardcoded_hits = []` | `{Doğrulama}` | **PASS** |

---

## 3. BOED Spektroskopi Ayrıntılı Bulgular (`N = 2,000` + Duyarlılık Analizi)

### 3.1 Sınıf Bazlı Aşama Süreleri (20 mK, 1.4 K LNA — Kilitli Temel Çizgi)

| Aday Sınıfı | Adet (`N=2,000`) | Kabul / Red | Stage 0 (ESR SPRT) | Stage 1 (10-Ton + İptal) | Stage 2 (Fisher BOED) | Toplam Ortalama | Medyan / P90 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `working` (`K=8`, `Δf >= 5 kHz`) | 996 | 994 / 2 | `0.73 ms` | `21.30 ms` | `52.46 ms` | **`74.49 ms`** | `73.85 / 82.73 ms` |
| `crowded` (`< 5 kHz` / eksik) | 515 | 0 / 515 | `0.73 ms` | `13.75 ms` | `0.11 ms` | **`14.58 ms`** | `15.33 / 17.74 ms` |
| `blank` (donör yok) | 489 | 0 / 489 | `0.73 ms` | `0.00 ms` | `0.00 ms` | **`0.73 ms`** | `0.73 / 0.73 ms` |
| **Tüm Popülasyon Ortalaması** | **2,000** | **994 / 1,006** | **`0.73 ms`** | **`14.15 ms`** | **`26.15 ms`** | **`41.03 ms`** | **`23.04 ms` medyan** |

### 3.2 Kriyojenik LNA ve 1 K PSB Rejim Duyarlılığı (`N = 400` / rejim)

| Okuma Rejimi (`Exp125` Çapası) | `τ_SNR10` (ms) | Ort. `t_spec` (ms) | Ham Hızlanma | `RMS` (Hz) | `FNR` / `FPR` | `1024 @ 15 ms` Net Verim |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **20 mK, 1.4 K LNA (Kilitli, `N=2000`)** | `0.0627` | **`41.03`** | **`24.37×`** | **`72.67`** | `%0.20` / `%0.00` | **`1.503 × 10⁹/gün` (Yazma-Sınırlı)** |
| 20 mK, 3.0 K LNA (Bozulmuş, `N=400`) | `0.1332` | `48.07` | `20.80×` | `70.59` | `%0.00` / `%0.00` | `1.503 × 10⁹/gün` (Yazma-Sınırlı) |
| 1 K PSB (`3.165×` ort., `S6.8=C`, `N=400`) | `0.5665` | `106.44` | `9.40×` | `85.26` | `%1.03` / `%0.00` | `1.503 × 10⁹/gün` (Yazma-Sınırlı) |
| Eski `v3.0` Sabit Tarama (Referans) | `0.0627` | `1,000.00` | `1.00×` | `200.00` | `%0.00` / `%0.00` | `1.973 × 10⁸/gün` (Okuma-Sınırlı) |

> **Kritik Sistem Bulgusu:** `1 K` sıcak-okuma (`S6.8 = C`, `3.165×` PSB ortalamalı) rejimi bile BOED ile `106.44 ms` ortalama sürede kalarak `131.33 ms` yazma tavanı geçiş eşiğinin altında kalır ve `1.503 × 10⁹` yazmaç/gün tavanını doldurabilir! Ancak 1 K rejiminde `crowded` iptal süresi `69.77 ms`'ye uzar ve `FNR = %1.03` (`2/195`) eşiğine yaklaşır; bu nedenle `20 mK / 1.4 K LNA` ana kilitli rejim olarak en geniş güvenlik marjını sağlar.

### 3.3 Fabrika Verim ve Canlı `Factory` (`200` Yuva) Doğrulaması

| Yapılandırma | Spektroskopi Modu | `t_spec` | Yazma Tavanı (`/gün`) | Okuma Kapasitesi (`/gün`) | Gerçekleşen Net (`/gün`) | Hızlanma (`v3.0`'a göre) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `MachineConfig.v300_baseline()` | Sabit `1.0 s` | `1,000.0 ms` | `1.503 × 10⁹` | `1.973 × 10⁸` | `1.973 × 10⁸` (Okuma-Sınırlı) | `1.00×` |
| **`MachineConfig.v400_bayesian()` (`1024 @ 15 ms`)** | **BOED (`$0` HW)** | **`41.03 ms`** | **`1.503 × 10⁹`** | **`4.810 × 10⁹`** | **`1.503 × 10⁹` (Yazma-Sınırlı)** | **`7.61×`** |
| `v4.0 BOED` (`1024 @ 10 ms` yükseltme) | BOED (`$0` HW) | `41.03 ms` | `2.254 × 10⁹` | `4.810 × 10⁹` | `2.254 × 10⁹` (Yazma-Sınırlı) | `11.42×` |
| `v4.0 BOED` (`2048 @ 15 ms` çift-dizi) | BOED (`$0` HW) | `41.03 ms` | `3.005 × 10⁹` | `4.810 × 10⁹` | `3.005 × 10⁹` (Yazma-Sınırlı) | `15.23×` |

Canlı `Factory` `200`-yuvalı entegrasyon testi: `v3.0` (`176` sertifikalı, `1,000.0 ms/deneme`) → `v4.0` (`170` sertifikalı, canlı ortalama **`39.75 ms/deneme`**, **`191` erken iptal**, `1.503 × 10⁹/gün`).

---

## 4. `CellISA v3.0` Çoklu-Hücre (`M4`) Derleyici ve `Exp126` 32D Köprüsü

### 4.1 Yeni Komut Seti (`VALID_OPCODES_V3`)
`CellISA v2.0`'daki 10 komut (`INIT`, `RX`, `RY`, `RZ`, `CNOT`, `CZ`, `GHZ`, `DD_HOLD`, `MEASURE`, `ARRAY_EXEC`) eksiksiz korunmuş; aşağıdaki 4 çoklu-hücre komutu eklenmiştir:
1. `WAFER_MAP_ROUTE` — Heterojen `4×4` wafer haritası üzerinde ölü (`blank`/`crowded`) yuvaları baypas ederek en düşük atlama sayılı ve en kısa fiziksel Manhattan izli bağlantılı çalışan hücre ağacını seçer (`WaferRouter`).
2. `BUS_TUNE` — Yüksek-empedanslı `NbTiN` (`Z_r = 2.5 kΩ`) dispersif kavite-QED veri yolunu (`g = 15 MHz`, `Δ = 150 MHz`, `κ = 0.50 MHz`, `T_2 = 500 µs`) ayarlar (`J_bus = g²/Δ = 1.50 MHz`).
3. `BUS_CZ` — İki farklı hücre arasında `t_CZ = 1/(4 J_bus) = 0.1667 µs` dispersif CZ kapısını tam `4×4` Kraus Purcell genlik sönümleme + $T_2$ faz bozulması yoğunluk matrisi kanalı ve her hücrenin kendine özgü `{A_k}` hiperince tayfına derlenen yerel nükleer RF `CNOT(e, n0)` darbesiyle yürütür.
4. `LOGICAL_ENCODE` — Yönlendirilen `4` hücreyi `bitflip3_plus_ancilla` tekrarlama koduna kodlar, `p_L = 3 p² - 2 p³` mantıksal hata baskılamasını hesaplar ve `SHA-256` imzalı `MultiCellCertificate` (`results/exp132_bayesian_spectroscopy_cellisa3/multicell_v300_demo.jsonl`) yazar.

### 4.2 Örnek `4×4` Wafer Sertifikası ve `Exp126` 32D Doğrulama Köprüsü

| Alan | Değer (`exp132.json` / `multicell_v300_demo.jsonl`) |
| :--- | :--- |
| Yönlendirilen Hücreler (`4×4`, `10` çalışan / `6` ölü) | `W000-R0C0` `(0,0)`, `W000-R1C0` `(1,0)`, `W000-R2C0` `(2,0)`, `W000-R1C1` `(1,1)` |
| Aktif `NbTiN` `BUS_CZ` Kenarları (tamamı `1`-hop, `Manhattan=1`) | `(0,0)-(1,0)`, `(1,0)-(2,0)`, `(1,0)-(1,1)` (`mean_bus_hops = 1.000`) |
| Baypas Edilen Ölü Yuvalar (`6`) | `(0,1)`, `(0,2)`, `(1,3)`, `(2,2)`, `(3,0)`, `(3,2)` |
| Yerel Hücre-Özgü Darbeler / Toplam Süre | `12` yerel MW+RF darbesi + `3` `BUS_CZ`; `T = 3,000.80 µs` |
| Kavite `BUS_CZ` / Kraus Bell / 4-Hücre Ortak Sadakat | `min_bus_cz = 0.988923`, `Kraus Bell = 0.994452`, **`F_joint = 0.983448`** |
| Mantıksal Hata Baskılaması (`bitflip3_plus_ancilla`) | `p_phys = 1.11%` → **`p_L = 0.0365%` (`3.65 × 10⁻⁴`, `30.3×` azalma)** |
| Spektral Kapı & Adreslenebilirlik | `min_gap = 25.89 kHz` (`>= 5 kHz`); `min_vandermonde_rank = 8/8` |
| `Exp126` `32D` 448-Seyirci Köprüsü (`verify_with_exp126_bridge`) | `Q_32D(α=1) = 0.9209`, `Q_32D(α=2) = 0.9433` (`P126_4 = PASS`), 16-hücre `Bell = 0.9501`, `GHZ4 = 0.9401`, `BitFlip-3 = 0.8878` |
| Kriptografik `SHA-256` Özeti | `0f4684194d061e8720004314a517bfc6ae13bc8e77f186e8ec7709fcace182cd` (`verified = True`) |

---

## 5. Kapsam Dışı / Varsayımlar ve Risk Notları (Epistemik Kalibrasyon)

- **`no_lab_measurement = true`:** Tüm BOED SNR eğrileri (`Exp125` çapa modeli) ve `NbTiN` kavite-QED dispersif `BUS_CZ` sadakatleri analitik/sayısal modellerdir (`{Model}` / `{Sayısal-Simülasyon}`); kriyostat içinde fiziksel silikon yonga ölçümü yapılmamıştır.
- **Soyutlama Sınırı (`CellISA v3.0` vs `Exp126` `32D`):** `MultiCellProgrammer` yerel RF/MW derlemesi hızlı `2^(N+1)` birim-üniter + `4×4` Kraus kavite-bus kanalını kullanır (`local_fidelity_product = 1.000000` gürültüsüz şekillendirilmiş RF tavanı); `448`-seyircili tam `32D` banyo + ara-serpiştirilmiş `XY8-GRAPE` gerçekçi gürültü tabanı `verify_with_exp126_bridge()` üzerinden `Exp126`'ya (`Q_32D_α2 = 0.9433`, `Bell = 0.9501`, `GHZ4 = 0.9401`) bağlanır.
- **1 K PSB Kenar Marjı:** `1 K` sıcak okuma (`3.165×` ortalama) duyarlılık taramasında `FNR = %1.03` ölçülmüştür; `1 K` opsiyonu seçilirse Stage 1 `coarse_tau_ro_ms` süresinin hafif artırılması (`~+15%`) önerilir (hâlâ `131.33 ms` yazma tavanı geçişinin altında kalır).

---

## 6. Üretilen Artefaktlar ve Doğrulama

- `src/machine_control/adaptive_spectroscopy.py` — 3 aşamalı BOED spektrometre (`BOEDConfig`, `BayesianSpectrometer`, `fisher_crlb_sigma_Hz`).
- `src/machine_control/programmer.py` — `CellISA v3.0` (`BusLinkSpec`, `WaferSite`, `WaferRouter`, `MultiCellCertificate`, `MultiCellProgrammer`, `verify_with_exp126_bridge`).
- `src/machine_control/config.py`, `factory.py`, `sim.py`, `__init__.py` — `MachineConfig.v400_bayesian()`, `Factory` adaptif BOED yolu, `--preset v400`.
- `experiments/exp132_bayesian_spectroscopy_cellisa3/run_exp132.py` ve `plot_exp132.py`.
- `results/exp132_bayesian_spectroscopy_cellisa3/predictions_exp132.json`, `exp132.json`, `exp132_plot_data.json`, `multicell_v300_demo.jsonl`, `fig_exp132_bayesian_speedup.png`, `fig_exp132_wafer_routing_cellisa3.png`, `summary_exp132.md`.
- `tests/test_exp132.py` + tam regresyon paketi: **`41/41 pytest PASS`**, sıfır sabitlenmiş konak yolu.
