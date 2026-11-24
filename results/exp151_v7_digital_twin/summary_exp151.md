# Exp151 (H169): v7.1 Bütünleşik Artefakt Özeti ve SHA-256 Dosya Bütünlüğü Manifestosu (TRL 1–2 / M0)

**Tarih:** 2026-11-24 | **Hipotez:** `H169` | **Sürüm:** `v7.1` (`v7.0` artefakt manifestosu yenilendi) | **Ön-Kayıtlı Yazılım Kontrolleri:** **`8/8 PASS` (`DT7_1..DT7_8`)**

> **Epistemik Kapsam ve Sınırlılıklar (`TRL 1–2 / M0`):**
> - **Kavramsal Sistem Tasarımı ve İndirgenmiş-Mertebe Çok-Fizikli Modelleme (`M0`):** Silikon `³¹P / ¹²¹Sb / ¹⁶⁷Er` fabrikasyon modelleri (`S1..S8`), nominal statik `CAD v6.0` (`199` parça; GD&T, termal büzülme, titreşim ve DFM hariç), parametrik `BOM v7.0` (`180` parça / `10-RFQ` taslağı, `no_supplier_quotes = true`), `Exp147` (`qLDPC d=18`), `Exp148` (`¹²¹Sb` `Q-Echo-8`), yapısal/bit-kesin Verilog RTL kontrolü (`Exp149`, `no_external_eda_sim = true`), `Exp150` sertifikasız ön emniyet FMEA/HAZOP tasarımı ve `auto_recal.py` benzetimi sayısal tasarım modellemesidir (`no_lab_measurement = true`, `tapeout_done = false`).
> - **Sertifikasız Emniyet Sınırı (`Exp150`):** `SEMI`, `SEMI S2` kılavuzu için sertifika vermez; `IEC 61508 SIL-3` ise bağımsız fonksiyonel emniyet değerlendirmesi ve tam donanım yaşam döngüsü gerektirir. Tablolardaki `SIL-3` / `SIL-2` sınıfları yalnızca hedeflenen ön tasarım mimarisini belirtir.
> - **Bulut Süperiletken-QPU Kontrol/Dekoder Proxy Kıyaslaması (`Exp145`):** `CellISA v4.0 → OpenQASM 3.0`, Hahn-Echo/XY4 DD, Bell tomografi, 5-kübit `d=3` tekrar kodu ve `Q16.16` BOED algoritmaları `ibm_marrakesh` (`156Q Heron r2`, `job_id = dc1tdo2nj2vs73dfrfl0`, `0` gizli anahtar sızıntısı) süperiletken bulut işlemcisinde çalıştırılmıştır; bu koşum **silikon `³¹P` fabrikasyon donanımını doğrulamaz**.
> - **Dosya Bütünlüğü ve Yazılım Testleri:** `SHA-256` özetleri yalnızca üretilen dosyaların sonradan değiştirilmediğini izleyen **dosya-bütünlüğü / izlenebilirlik özetidir** (bilimsel doğrulama veya sertifikasyon değildir); `306/306 pytest` yalnızca kodun iç tutarlılığını ve yeniden üretilebilirliğini sınar.

---

## 1. Dosya Bütünlüğü ve İzlenebilirlik Manifestosu (Tam 64-Hex `SHA-256` — Bilimsel Kanıt Değil)

- **`v7_digital_twin_cert.json` Kanonik JSON `SHA-256` (Tam 64-Hex — Dosya Bütünlüğü Özeti):**
  `7a3dca56839c1d4aefedf01c61fd5f6b1c62f498f45d9a2329568f04cc437d43`
- **Bulut QPU Proxy Ham Sayım Defteri (`results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json`) `SHA-256`:**
  `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a`
- **Çevrimdışı HTML5 Model Gezgini (`docs/digital_twin_interactive.html`, `67.505` bayt, `5` sekme, `0` CDN) `SHA-256`:**
  `e78b7e9a61ecc19ce753765ed23be20d6544e2f37ccc23e2516ffd1d1197fc61`
- **İzlenen Artefakt Sayısı:** **`38 / 38`** (`27` deney JSON'u `Exp124..Exp150` + `1` IBM QPU proxy JSON + nominal `CAD v6.0` + parametrik `BOM_DETAILED.csv v7.0` + `7` `rtl/boed_fpga/` dosyası + `docs/digital_twin_interactive.html`).
- **Dokunulmadan Korunan Tarihsel Dosya-Bütünlüğü Manifestoları:**
  - `v4_digital_twin_cert.json`: `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57`
  - `v5_digital_twin_cert.json`: `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`
  - `v6_digital_twin_cert.json`: `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7`

---

## 2. Ön-Kayıtlı `DT7_1 .. DT7_8` Yazılım Tutarlılık Tablosu (`8/8 PASS`)

| Kontrol ID | Kapsam | Ölçülen Model / Dosya Bulguları | Sonuç |
| --- | --- | --- | --- |
| `DT7_1_LEDGER_CAD_BOM_RTL_TWIN_SHA256_LOCK` | `38/38` `SHA-256` + CAD v6 + BOM v7 | `27` deney JSON + nominal statik `CAD v6.0` (`199p`, `1.108,137 kg`, `0/19.701` statik çakışma, `40/40` zarf; GD&T/termal/DFM hariç) + parametrik `BOM v7.0` (`180p`, `$0,00` köprü, `0,0000 kg` şasi + `355,0 kg` tesis = `1.463,137 kg`, `10-RFQ` taslağı `%78,24` nom / `%92,58` var) + `7` RTL + HTML5 gezgin | **PASS** |
| `DT7_2_UNIVERSAL_QLDPC_D18_AND_ALGORITHMS` | `Exp147` `qLDPC d=18` | `[[288,12,18]]` `L_max = 268,3 µm <= 300`, `p_th = %0,781`, `576`-hücre `%99,27 (N=8)` / `%99,82 (N=9)`; FeMoco `16` kriyo / `3,38 sa` / `$6.537` (`37,06x`, dürüst `UQ5` okuma-tavanı notu); RSA-2048 `291` kriyo / `7,37 MW` / `21,13 sa` (`52,67x`) | **PASS** |
| `DT7_3_SB121_QECHO8_CLOSURE_AND_SU8_GRAPE` | `Exp148` `¹²¹Sb` `Q-Echo-8` | Statik `500 Hz` Gross `0,5800 -> 0,99908` (`455,5x` model infidelite düşüşü, `Exp142 OQ6` model iterasyonu), Cat `0,9424 -> 0,99914`, `SU(8)` GRAPE `X_L/Z_L/H_L >= 0,9954`; dürüst Cywiński `1/f` sınırı (`SQ4 FAIL`, `Q-Echo-8: 8,39x`, `Q-Echo-64: 28,08x = 1,45 ms`) | **PASS** |
| `DT7_4_VERILOG_RTL_AND_INTERACTIVE_TWIN` | `Exp149` RTL + HTML5 Gezgin | `4` sentezlenebilir IEEE 1364-2005 `.v` (`894` satır, `0` lint/port/genişlik hatası), `1.024/1.024` ROM `0`-bit, `64/64` golden + `1.000` `isqrt` `0 LSB`, `584` çevrim (`2,336 µs @ 250 MHz`), `4` çevrim SPRT, `ZU48DR` DSP `%10,49` / `0 W` kriyo, `no_external_eda_sim=true`, HTML5 `0` CDN / `0` sızıntı | **PASS** |
| `DT7_5_INDUSTRIAL_SAFETY_FMEA_HAZOP_SEMI_S2` | `Exp150` Sertifikasız Ön Emniyet | `7/7 PASS`, `25` FMEA + `10` HAZOP taraması, `max RPN 280 -> 42 <= 60` (`-%86,3` ortalama, `0` artık `>60`), `OD=8 + 3 mm` çelik Lazer+X-ışını modeli (`1,19e-23 µSv/h`, `3,2 ms` SIL-3 hedef perde), sub-atm `SDS PH₃` `0,00715 ppm`, He `O₂ = %20,57`, `15 kVA` UPS `40/213 dk`, `S7.SAFETY = $145.000 / 355,0 kg / 1.090 W` (sertifikasız `M0` tasarım hedefi) | **PASS** |
| `DT7_6_LIVE_IBM_QPU_CELLISA40_AND_EPISTEMIC_BOUNDARY` | `Exp145` Bulut QPU Proxy | `ibm_marrakesh` (`156Q`, `job_id=dc1tdo2nj2vs73dfrfl0`, silikon-dışı kontrol proxy, `0` sızıntı): Bare `0,3325 -> XY4 0,9280` (`+59,55 pp`), Bell `F = 0,9733`, `d=3` `5,16x / 7,83x` (`postsel %0,000`), `Q16.16` BOED `3` nokta `1,6 Hz` fark; `CellISA v4.0` (`20` opcode) + `auto_recal` sim (`4/4 PASS`) | **PASS** |
| `DT7_7_MODULAR_V7_BUDGET_CAP_AND_PHASED_PROCUREMENT` | `Exp128 v7.0` Parametrik Fazlı Bütçe | `M3 Base $5,248M (%4,44)`, **Faz-1 `Base+Safety $5,393M (%4,67 < %5, 6/6 CU PASS)`**, `v6 Full $5,548M (%4,95)`, dürüst `v7 Full $5,693M (%5,22 > %5 -> RFQ-05 fiyat kilidi sonrası Faz-2 +Option-Q/HPC)` | **PASS** |
| `DT7_8_CRYPTO_V7_CERT_PORTABILITY_AND_TESTS` | Dosya Bütünlüğü ve Hijyen | `v7_digital_twin_cert.json` `SHA-256` dosya bütünlüğü kontrolü ve tahrifat tespiti aktif (yalnızca değiştirilmezlik kontrolü), `v4/v5/v6` manifestoları dokunulmamış, `0` mutlak yol, `0` sır/token | **PASS** |

---

## 3. `v3.0 → v7.1` Evrim ve Modüler Parametrik Bütçe Özeti

| Katman / Konfigürasyon | Parça (BOM / Nominal CAD) | M3 BOM (Nom USD) | Kütle (Şasi / Tesis) | `P(Prog > $100M)` | Mimari ve Program Rolü |
| --- | --- | --- | --- | --- | --- |
| `v3.0 Base` | `— / —` | `$4,189,600` | `—` | `—` | İlk kavramsal atom litografi temel modeli (`Exp124..128`) |
| `v4.0 Base` | `— / —` | `$4,609,600` | `—` | `—` | Flaş tavlama `S5.5` + `M4` veri yolu modeli (`Exp129..135`) |
| `v5.0 Base` | `167 / 189` | `$5,247,800` | `1,034.937 kg / 0 kg` | `%4.44` (`PASS`) | `f*=%1.5+Stark`, `1530 K` TED model iterasyonu, `N_mux*=32`, `100L D2 SC: 679` kriyostat |
| **Faz-1 `v7.0 Base+Safety`** | **`173 / 189`** | **`$5,392,800`** | **`1,034.937 / +355.0 kg`** | **`%4.67` (`PASS`)** | **Önerilen Faz-1 (+Ön Emniyet Kiti, Sertifikasız `M0`): `6/6 CU PASS`, `<%5` tavan içi** |
| `v6.0 Full (+Q+HPC)` | `174 / 199` | `$5,547,800` | `1,108.137 kg / 0 kg` | `%4.95` (`PASS`) | `D3 GRAPE` (`100` kriyo) + `qLDPC [[144,12,12]]` (`1` kriyo, `108L`, `$63.8k/L_sys`) + IBM QPU Proxy |
| `v7.0 Full (+Ön Emniyet Kiti, Sertifikasız M0)` | `180 / 199` | `$5,692,800` | `1,108.137 / +355.0 kg` | `%5.22` (Dürüst `>%5`) | Faz-2 hedefi: Faz-1 `Base+Safety` → `RFQ-05` fiyat kilidi → `+Option-Q` ve `+Option-HPC` yükseltmesi |

---

## 4. Dürüst Fiziksel, Modelleme ve Sertifikasyon Sınırları

1. **`Exp147` (`UQ4` / `UQ5` Dürüst FAIL):** `[[288,12,18]]` kodu `L_max = 268,3 µm <= 300 µm` ve `FeMoco` için `16` kriyostat (`37,06x` model sıkıştırması) verse de `2–3 µs` okuma tavanı (`p_meas = %0,22–%0,39`) `d=18` bellek hata tabanını sınırlar; `p_fail_mem < %1` için `D3++` (`p_2q <= %0,20`, `p_meas <= %0,10`) veya `d=24` gereklidir.
2. **`Exp148` (`SQ4` Dürüst FAIL):** `Q-Echo-8` statik `500 Hz` dört-kutuplu gürültü modelinde `455,5x` hata azalmasıyla `0,99908` değerine ulaşarak `Exp142 OQ6` kısıtını model uzayında giderir (deneysel doğrulama yok); ancak geniş bant `1 Hz–100 kHz` `1/f` gürültüsü altında Cywiński ölçeklemesi nedeniyle tek çevrim `Q-Echo-8` `8,39x` verirken çok-çevrimli `Q-Echo-64` `28,08x` (`1,45 ms`) düzeyine ulaşır.
3. **`Exp149` (`no_external_eda_sim = true`):** Konak makinede ticari/açık EDA sentezleyici (`iverilog`/`verilator`/`vivado`) bulunmadığından kontrol yalnızca yapısal IEEE 1364-2005 lint + `1.024/1.024` ROM `.hex` + `64/64` bit-tam altın vektör Python eş-doğrulamasıyla yapılmıştır; gerçek `ZU48DR` bit-akışı sentezi ve zamanlama kapanışı Vivado adımına tabidir.
4. **`Exp150` (Sertifikasız Ön Emniyet Tasarım Hedefi):** `SEMI`, `SEMI S2` için sertifikasyon vermez; `IEC 61508 SIL-3` ise bağımsız fonksiyonel emniyet değerlendirmesi ve donanım yaşam döngüsü kanıtı gerektirir. `RPN 280 -> 42` düşüşü yalnızca ön `M0` tasarım taramasıdır.
5. **`Exp128 v7.0` (`v7 Full` Dürüst `%5,22`):** Tüm seçeneklerin (`S7.SAFETY + Option-Q + Option-HPC`) tek seferde alınması `P(Prog > $100M) = %5,22` ile `%5` tavanını marjinal aşar; bu nedenle **Faz-1 `Base+Safety` (`%4,67 < %5`) → `RFQ-05` fiyat kilidi → Faz-2 `+Q/+HPC`** fazlı tedarik stratejisi öngörülmüştür (`no_supplier_quotes = true`).
6. **Ölçüm / Tedarikçi / Proxy Sınırı:** Silikon-dışı `ibm_marrakesh` bulut QPU kontrol/dekoder proxy kıyaslaması dışında hiçbir deneysel laboratuvar ölçümü veya gerçek tedarikçi teklifi mevcut değildir (`TRL 1–2 / M0`). Kapanış onayı (`KABUL`) sıfır bağlamlı bağımsız Carbon denetimine aittir.

![Exp151 Bütünleşik Artefakt Özeti ve Dosya Bütünlüğü Manifestosu](fig_exp151_v7_digital_twin.png)
