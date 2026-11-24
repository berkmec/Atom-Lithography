# Exp127 — 8-Kanallı IBIC Ön-Uç Fiziksel Devre Simülasyonu, Lindhard Gürültü/Verim Bütçesi & `machine_control` v2.0

Tarih: 2026-11-22. **Epistemik durum: `{Model}` & `{Aday-COTS}`; `no_lab_measurement=true` (fiziksel kart/PCB/laboratuvar ölçümü yoktur).**

## 1. Kapsam ve Tasarım Yenilemesi
Bu deney iki kritik eksiği kapatır:
1. **`src/board/` IBIC 8-Kanallı Ön-Uç Onarımı (`COLD_100K` Kilitli Varsayılan):** Eski `detector_frontend.net` üzerindeki tüm topolojik kusurlar giderildi (boşta op-amp girişleri, çift-nete bağlı pinler, eksik CR-RC pasifleri, paylaşımlı DAC ve jenerik yer tutucular). `detector_frontend.py` varsayılan olarak kilitli **`COLD_100K`** profilini (`RF = 1 GΩ`, `CS = CP = 600 pF → τ_s = 1,2 µs`, `Q_ION = 0,055 fC`, `V_THR = 4,23 mV`; isteğe bağlı `--profile rt300k`) üretir: geçerli KiCad S-ifadesi (`detector_frontend.net`: **204 bileşen, 107 benzersiz net, 0 ERC hatası**) ve standart SPICE destesi (`detector_frontend.cir`).
2. **Analitik/SPICE Benzeri Devre + Monte Carlo Simülasyonu:** `Exp72`'nin sezgisel varsayımları (`Y_e = 0,35/0,40/0,45` ve `ENC = 50 + 25·C`) yerine tam **Lindhard elektronik/nükleer durdurma bölüşümü**, sonlu GBP'li **Laplace `H(s)` + sıfır-sarmallı zaman-alanı darbe tepkisi**, **Parseval gürültü integrali `ENC(C_det, τ_s, T)`**, **Rice yanlış-tetik oranı** ve nokta başına **`50.000` iyonlu Monte Carlo** yürütüldü.

## 2. Kayıtlı Öngörüler & Hükümler (`predictions_exp127.json`)

| Kimlik | Öngörü | Ölçülen Model Sonucu | Hüküm |
|---|---|---|---|
| `CZ1_LINDHARD_MONOTONIC` | `Y_e(20) > Y_e(10) > Y_e(5)`, `5 keV` `[300, 420] e⁻` | `Y_e = 0,2542 / 0,2867 / 0,3281`; `S(5 keV) = 351,2 e⁻` (300 K) / `341,7 e⁻` (100 K) | **PASS** |
| `CZ2_LAPLACE_PEAK_AND_BALLISTIC` | `t_peak ≈ 200 ns` (±15%), `50× Q/Cf` (±10%), ODE tutarlılığı | `t_peak = 224,66 ns`, FFT `35,200 mV` vs ODE `35,201 mV` (`%0,004` fark; ideal `35,604 mV`) | **PASS** |
| `CZ3_ENC_NOISE_CORNER` | `RT 300 K (Rf=100 MΩ)` `τ_opt`'ta `≥ %25` ENC düşüşü | `RT`: `89,9 → 80,9 e⁻` (`@500 ns`, yalnız `−%10,1`, çünkü `Rf=100 MΩ` akım tabanı erken yakalar). *(Not: `Cold 100 K / Rf=1 GΩ` kolunda `42,1 → 24,1 e⁻ @1200 ns`, `−%42,8`!)* | **FAIL** *(dürüst çürütme)* |
| `CZ4_RT200NS_5KEV_EXPOSED` | `RT 200 ns` `5 keV`'de başarısız, `10 keV`'de `≥ 0,99` | `RT 200 ns @0,5 pF`: `5 keV η = 0,0972` (çöker); `10 keV η = 0,9774` (`≥0,90` ama Lindhard yüzünden `0,99` hedefinin hemen altında!) | **FAIL** *(10 keV için de `1 GΩ / 1,2 µs` gerektiğini gösterdi)* |
| `CZ5_COLD_OPT_5KEV_CLOSES` | `Cold 100 K / 1,2 µs / Rf=1 GΩ`: `ENC < 35 e⁻`, `η(5 keV) ≥ 0,99`, `P_false < 10⁻³` | **`ENC = 24,1 e⁻ rms`**, **`η(5 keV, 0,5 pF) = 0,99936`**, **`P_false = 2,59×10⁻⁴ / 1 ms`** | **PASS** |
| `CZ6_ERC_CLEAN` | `0` ERC hatası, `8` bağımsız SPI-DAC eşik kanalı | `204` bileşen, `107` net, **`0` ERC hatası** | **PASS** |

## 3. Anahtar Fiziksel Bulgular (Makine Tasarımı İçin Kritik!)

1. **Lindhard Düzeltmesi (`Exp72` Revizyonu):** Gerçek Lindhard durdurma bölüşümü (`Z1=15, M1=30,974 → Si`), `Exp72`'nin sezgisel varsayımının (`486 / 1111 / 2500 e⁻`) ~%28 altındadır:
   - `5 keV`: `351,2 e⁻` (300 K) / `341,7 e⁻` (100 K, `w_Si = 3,72 eV`)
   - `10 keV`: `792,0 e⁻` (300 K) / `770,8 e⁻` (100 K)
   - `20 keV`: `1813,0 e⁻` (300 K) / `1764,2 e⁻` (100 K)
2. **CR-RC Balistik Faktör (`1/e`) Düzeltmesi:** `BOARD.md` v1 `×50` şekillendirici kazancında `1/e = 0,3679` balistik zayıflamayı ihmal etmişti. Yeni `ADA4817-1` `{Aday-COTS}` katı `RG1 = 100 Ω, RG2 = 13,5 kΩ` (`G_stage = 136`) ile net tepe kazancını `G/e = 50,03` (`198,2 mV/fC` @ `1111 e⁻ → 35,20 mV`) olarak kalibre eder.
3. **P91 `5 keV` İçin Soğuk Ada (`100 K`) + `1,2 µs` Şekillendirme Şartı (`C_det` Taraması, `50.000` İyon/Nokta, `5,5σ` Rice Eşiği):**

| Ön-Uç Rejimi | `C_det` (pF) | `ENC` (`e⁻` rms) | `P_false` (1 ms) | `η (5 keV P91)` | `η (10 keV)` |
|---|---:|---:|---:|---:|---:|
| `RT 300 K / 200 ns / 100 MΩ` | `0,50` | `89,9` | `8,06×10⁻⁴` | `0,0972` (**FAIL**) | `0,9774` |
| `RT 300 K / 1,2 µs / 1 GΩ` | `0,50` | `58,1` | `1,63×10⁻⁴` | `0,6455` (**FAIL**) | **`0,99978`** |
| **`Cold 100 K / 1,2 µs / 1 GΩ`** | `0,20` | `22,1` | `2,56×10⁻⁴` | **`0,99962`** | **`1,00000`** |
| **`Cold 100 K / 1,2 µs / 1 GΩ`** | **`0,50`** | **`24,1`** | **`2,59×10⁻⁴`** | **`0,99936`** | **`1,00000`** |
| **`Cold 100 K / 1,2 µs / 1 GΩ`** | `1,00` | `27,9` | `2,67×10⁻⁴` | **`0,99738`** | **`1,00000`** |
| **`Cold 100 K / 1,2 µs / 1 GΩ`** | `1,50` | `32,2` | `2,79×10⁻⁴` | **`0,99064`** | **`1,00000`** |
| **`Cold 100 K / 1,2 µs / 1 GΩ`** | `2,00` | `36,8` | `2,95×10⁻⁴` | `0,97300` | **`1,00000`** |

**Tasarım hükmü:** P91 `5 keV ³¹P⁺` noktasında `η ≥ 0,99` penceresini açmak için CSA ilk kademesi soğuk ada (`T ≈ 100 K`, `R_f = 1 GΩ`) üzerinde `τ_s = 1,2 µs` (`CS = CP = 600 pF`, `1 ms` atış çevriminin `< %0,2`'si) ile çalıştırılmalıdır; bu rejimde **`C_det ≤ 1,5 pF`** bandının tamamında `η(5 keV) ≥ 0,99` sağlanır (`C_det = 0,5 pF` tasarım noktasında `3×` kapasitans marjı ve `η = 0,99936`).

## 4. `machine_control` v2.1 & `CellISA` Sayısal Benzetim ve Yazılım Demo Özeti (`Arch-B` `1.024` Demetcik Kilidi)
- **Fabrika demo sertifikaları (`certs_v224_demo.jsonl`, 4000 yuva, `v224_baseline` / `v300_baseline`):** Kilitli `Arch-B` `1.024` demetcik (`32×32 @ 0,50 mm = 16,0×16,0 mm`, `16×` 64-kanallı karo) ve `Exp124 HDA-HiRes` `15 ms/atış` (`2,95×10⁹` ham atış/gün `@%50` görev `≫` okuma sınırı); `3517/4000` sertifikalı (`%87,92`), `1,98` atış/yazmaç, `1,98` spektroskopi/yazmaç, analitik hız **`1,973×10⁸`/gün** (`56×160 = 8960` okuma kanalı), **`3517/3517` kayıtta 8 elemanlı `lines_Hz` %100 dolu**.
- **`CellISA` GRAPE Derleyici (`prog_certs_v224_demo.jsonl`, 9 köşe `±400 Hz × ±2%`, SHA-256 imzalı; `DD_HOLD` hızlı efektif koherens faz operatörü — tam 32B `448`-seyirci `XY8-GRAPE` doğrulaması `Exp126`'dadır):**
  - `bell` (2 darbe): `F_nom = 0,9940`, **`F_corner_min = 0,9982`**, `XY8 DD gain = 14,37×`, SHA-256 PASS.
  - `ghz` (4 kübit, 4 darbe): `F_nom = 0,9948`, **`F_corner_min = 0,9950`**, `XY8 DD gain = 14,37×`, SHA-256 PASS.
  - `repcode3` (3 kübit, 3 darbe): `F_nom = 0,9987`, **`F_corner_min = 0,9927`**, `XY8 DD gain = 14,37×`, SHA-256 PASS.
  - `qft3` (3 kübit, 72 darbe): `F_nom = 0,9893`, **`F_corner_min = 0,8812`** (`F_corner_mean = 0,9633` — şekilli Gauss'ta `0,0153`'ten `57×` artış!), SHA-256 PASS.

## 5. Üretilen Artefaktlar
- `results/exp127_detector_frontend_sim/predictions_exp127.json`
- `results/exp127_detector_frontend_sim/exp127.json` & `exp127_traces.json`
- `results/exp127_detector_frontend_sim/fig_exp127_schematic_block.png` (`1920×1200`)
- `results/exp127_detector_frontend_sim/fig_exp127_bode_transient.png` (`1920×1200`)
- `results/exp127_detector_frontend_sim/fig_exp127_enc_eta_mc.png` (`1920×1200`)
- `results/exp127_detector_frontend_sim/certs_v224_demo.jsonl` & `prog_certs_v224_demo.jsonl`
