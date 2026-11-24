# Exp145 (H163): Bulut Süperiletken QPU Kontrol/Dekoder Kıyaslaması (`ibm_marrakesh` Proxy — Silikon Fabrikasyonunu Doğrulamaz) ve `auto_recal.py`

**Deney / Hipotez:** `exp145_cloud_qpu_ibm_validation` (`H163`)  
**Veri Defterleri:** `results/exp145_cloud_qpu_ibm_validation/exp145.json`, `exp145_offline.json`, `ibm_qpu_live_results.json`, `predictions_exp145.json`  
**Görsel:** `results/exp145_cloud_qpu_ibm_validation/fig_exp145_ibm_qpu_live.png` (`2400×1400`)

---

## 1. Epistemik Sınır ve Kapsam Beyanı (Silikon Fabrikasyonunu Doğrulamaz)

> **Kritik Kapsam Sınırı:** Bu çalışmadaki süperiletken transmon bulut işlemcisi (`ibm_marrakesh`, `156Q Heron r2`, `job_id = dc1tdo2nj2vs73dfrfl0`) koşumu yalnızca yazılım kontrol/dekoder yığınının (`CellISA v4.0 → OpenQASM 3.0`, `Echo/XY4` DD, `d=3` tekrar dekoderi ve bit-kesin `Q16.16` BOED) **silikon-dışı bir bulut QPU proxy kıyaslamasıdır**. Bu koşum silikon `³¹P` implantasyonu, flaş tavlama, epitaksiyel MBE, `100 K` IBIC veya herhangi bir atom-litografi donanımını **hiçbir şekilde doğrulamaz** (`TRL 1–2 / M0`, `no_lab_measurement = true`).

Bu çalışmada iki farklı epistemik kanıt sınıfı birbirinden kesin çizgilerle ayrılmıştır:

| Bileşen | Epistemik Etiket | Gerçek Fiziksel Ölçüm Durumu |
| :--- | :--- | :--- |
| Silikon `³¹P` atom litografisi üretimi (`S1–S8`) | `{Model}` / `{Sayısal-Simülasyon}` | `no_lab_measurement = true` (`TRL 1–2 / M0` tasarım aşaması; fiziksel yazıcı/örnek yok) |
| `auto_recal.py` 4-arıza kapalı çevrim kurtarma (`CQ6`) | `{Model}` / `{Sayısal-Simülasyon}` | `no_lab_measurement = true` (fiziksel alt sistem modelleri üzerinde benzetim) |
| Offline IBM Heron gürültü simülatörü (`exp145_offline.json`) | `{Model}` / `{Sayısal-Simülasyon}` | Çevrimdışı referans model |
| **`CellISA v4.0` → OpenQASM 3.0 → IBM QPU Proxy (`C1`, `C2`, `C3`)** | **`{Bulut-QPU-Proxy-IBM}` (Silikon-Dışı)** | **156-kübitlik süperiletken `ibm_marrakesh` (Heron r2) bulut işlemcisinde kontrol/dekoder kıyaslaması (`job_id = dc1tdo2nj2vs73dfrfl0`, `32,54 s`, `16 PUB × 4.096 shot`, sıfır sızıntı; silikon fabrikasyonunu doğrulamaz)** |

---

## 2. Yazılım Mimarisi (`CellISA v4.0` ve Sıfır-`qiskit` REST Köprüsü)

1. **`CellISA v4.0` (`src/machine_control/programmer.py`, `v4.0.0`):**
   - Yeni 3 üst-düzey işlem kodu eklendi (`VALID_OPCODES_V4`): `QRAM_SWAP`, `QLDPC_ROUND`, `AUTO_RECAL`.
   - Toplam işlem kodu sayısı **`20`** (`VALID_OPCODES_ALL`), geriye dönük `v3.5` uyumluluk kümesi **`len(VALID_OPCODES) == 17`** dokunulmadan korunarak tüm `Exp140`/`Exp141` testleriyle %100 uyumluluk sağlandı.
   - `MultiCellProgrammer.execute_qram_swap()` (`F = 0,999893`), `execute_qldpc_round()` (`[[144,12,12]]` BB kodu, `5` besleme hattı, `p_L ≈ 6,0×10⁻⁶/tur`) ve `execute_auto_recal()` canlı yöntemleri eklendi.
2. **Sıfır-`qiskit` Saf-`requests` IBM Quantum Platform 2026 Köprüsü (`src/machine_control/cloud_qpu_bridge.py`):**
   - IBM Cloud IAM (`POST /identity/token`) + bölgesel CRN otomatik algılama (`eu-de` / global) + otomatik `IBM-API-Version` geri dönüşü (`2026-02-01` → `2026-04-15` → `2025-05-01`).
   - Tüm 4 IBM `SamplerV2` çıktı biçimini (hex `samples`, ikili `samples`, `counts` sözlüğü, iç-içe `__value__` / base64+zlib `BitArray`) tek çözücüde (`parse_sampler_v2_counts`) normalize eder.
   - Ağır-Altıgen (Heavy-Hex) topolojisinde `0` SWAP gerektiren küresel-optimal 5-kübitlik doğrusal zinciri (`select_best_linear_chain`) 2Q kapı hatası, okuma hatası ve `T₂` ağırlıklarına göre `< 5 ms`'de seçer.
   - Hem **IBM Heron (`cz`)** hem **IBM Eagle (`ecr`)** için kesin üniter (`< 10⁻¹²` hata) native-ISA `OpenQASM 3.0` üretir; `granularity = max(16, ...)` `16-dt` zamanlama hizasını statik olarak doğrular.
   - **Gerçek Donanımda Yakalanan API Düzeltmesi (`ibm_fez` v1 → `ibm_marrakesh` v2):** İlk canlı deneme (`ibm_fez`, `156Q`, `job_id = dc1tbginj2vs73dfrd60`, `32,77 s`) ilk seferde çalışıp `Bell F = 0,9196` ve `C2 d=3` `77,05×` hata bastırması verirken, IBM 2026 REST `/configuration` uç noktasının `"dt": 4.0` alanını **nanosaniye** (eski `4e-9` saniye yerine) döndürdüğünü ortaya çıkardı. `parse_backend_metrics()` içindeki `dt_s = raw_dt * 1e-9 if raw_dt > 1e-3 else raw_dt` normalizasyonu ve `test_ibm_2026_rest_nanosecond_dt_normalization` regresyon testiyle kök-neden kalıcı olarak giderildi ve `ibm_marrakesh` üzerinde tam salınımlı v2 verisi alındı.

---

## 3. Bulut QPU Proxy (`ibm_marrakesh`, 156Q Heron r2) vs Offline Heron Model Karşılaştırması

Seçilen 5-kübitlik doğrusal zincir: **`[q2, q3, q4, q5, q6]`** (`CZ` hata: `%0,14–%0,23`; okuma hatası: `%0,31–%2,78`; `T₁ = 128,6–342,9 µs`; `T₂ = 150,0–304,4 µs`).

| Devre / Metrik | Bulut QPU Proxy (`ibm_marrakesh`, Silikon-Dışı) | Offline Heron Model (`{Model}`) | Ön-Kayıt Eşiği | Durum |
| :--- | :---: | :---: | :---: | :---: |
| `C1a` Bare Idle `P(0)` (`48,128 µs`) | `0,3325` | `0,5625` | Referans taban | — |
| `C1b` Hahn-Echo `P(0)` (`48,128 µs`) | `0,9224` (`+59,0 pp`) | `0,8428` (`+28,0 pp`) | `> Bare Idle` | `PASS` |
| `C1c` XY4 DD `P(0)` (`48,128 µs`) | `0,9280` (`+59,5 pp`) | `0,8591` (`+29,7 pp`) | `> Bare Idle` | `PASS` |
| `C1d–f` 2Q Bell `F(Phi+)` (`q2, q3`) | **`0,9733`** (`ZZ=+0,961; XX=+0,972; YY=-0,960`) | `0,9530` | `>= 0,85` canlı / `>= 0,95` model | `PASS` |
| `C2` `d=3` Ham Fiziksel Hata (`avg p_phys`) | `0,02962` (`%2,96`) | `0,02975` (`%2,97`) | Referans | — |
| `C2` `d=3` Uzay-Zaman Sendrom MWPM (`avg p_L`) | `0,00574` (**`5,16×`** bastırma) | `0,00391` (`7,61×`) | `< 0,5 × p_phys` | `PASS` |
| `C2` `d=3` Veri Çoğunluk Dekoderi (`avg p_L`) | **`0,00378`** (**`7,83×`** bastırma) | `0,00195` (`15,23×`) | `< 0,5 × p_phys` | `PASS` |
| `C2` `d=3` Sıfır-Sendrom Post-Seçim (`avg p_L`) | **`0,00000`** (`0/7.451` hata; `%91,0` tutma) | `0,00027` (`%91,6` tutma) | Ek doğrulama | `PASS` |
| `C3` Ramsey Blind-8pt Frekansı (`1,02–8,00 µs`) | `120,479 kHz` (`std = 0,56 kHz`) | `125,679 kHz` | `125,0 kHz` programlı | Bilgi |
| `C3` FP64 BOED (uyarlamalı `3` nokta) | `120,107 kHz` (`std = 0,77 kHz`) | `125,851 kHz` | `<= 5` nokta | `PASS` |
| `C3` Bit-Kesin `Q16.16` BOED (uyarlamalı `3` nokta) | **`120,106 kHz`** (`std = 0,78 kHz`) | `125,852 kHz` | `<= 5` nokta (`2,67×` hızlanma) | `PASS` |
| `C3` `Q16.16` vs `FP64` Nicemleme Farkı | **`0,0016 kHz` (`1,6 Hz`)** | `0,0007 kHz` (`0,7 Hz`) | `< 0,5 kHz` | `PASS` |
| `C3` `Q16.16` vs Canlı `Blind-8pt` Farkı | **`0,3733 kHz`** | `0,1729 kHz` | `<= 3,0 kHz` | `PASS` |

### `C1` ve `C3` Arasında Bağımsız Fiziksel Çapraz-Doğrulama (`q2` `-4,52 kHz` Doğal Kayma)

Canlı `ibm_marrakesh` `C3` Ramsey saçağında ölçülen `8` ham olasılık `[0,854; 0,546; 0,200; 0,029; 0,099; 0,392; 0,723; 0,953]` temiz bir tam periyot kosinüs salınımı oluşturmuştur; ancak programlanan `125,00 kHz` yerine **`120,48 kHz`** (`δf_q2 = -4,52 kHz`) frekansına kilitlenmiştir. Bu durum bir kestirici hatası değil, fiziksel `q2` süperiletken kübitinin son kalibrasyondan bu yana yaşadığı gerçek **`-4,52 kHz`** rezonans kaymasıdır ve **`C1a_bare_idle`** ölçümüyle bağımsız olarak çapraz-doğrulanır: `48,128 µs` çıplak beklemede `q2` fazı `π/2`'yi geçerek `P(0) = 0,3325 < 0,50` bölgesine dönmüş, ardından `Hahn-Echo` (`0,9224`) ve `XY4` (`0,9280`) dinamik ayrıştırma darbeleri bu statik frekans kaymasını neredeyse tamamen geri odaklayarak **`+59,55` yüzde puan** koherans kazancı sağlamıştır. Bit-kesin **`Q16.16` BOED** çekirdeği düz ve tarafsız `[30, 220] kHz` önsel dağılımıyla yalnızca **`3` uyarlamalı nokta** (`[1,984; 6,976; 6,016] µs` — en dik eğimli sıfır-geçiş noktaları!) seçerek canlı `blind-8pt` frekansını **`0,373 kHz`** doğrulukla ve `FP64` BOED ile **`1,6 Hz`** pariteyle yakalamıştır (`CQ5` programlı `125 kHz`'e göre mutlak fark `4,89 kHz` olup gerçek `q2` `-4,52 kHz` kaymasından kaynaklanır; offline sıfır-kayma kıyaslamasında hata `0,85 kHz <= 3,0 kHz` ile `PASS`).

---

## 4. `CQ6`: `auto_recal.py` Otonom Arıza Kurtarma (`{Model}`, `4/4 PASS`)

| Arıza Senaryosu | Enjekte Edilen Arıza | Açık Çevrim Sonucu | `auto_recal.py` Kapalı Çevrim Sonucu | Eşik | Karar |
| :--- | :--- | :--- | :--- | :--- | :---: |
| (a) `S5.5` Lazer Güç Kayması | `±%8,0` optik güç kayması | `T_peak = 1628 K`; `σ_anneal = 0,787 nm` (`FAIL`) | `80 µs` AOM+PI servo; `σ_anneal = 0,3547 nm` | `<= 0,50 nm` | `PASS` |
| (b) `S5` UHV Vakum Sıçraması | `3,5×10⁻⁸ Torr` patlama | Korunmasız yüzey kontaminasyonu | `1,0 ms` PLC kilit; sürgülü vana kilitli; demet duraklatıldı; `0,0005 ML` maruziyet; `38,0 s` güvenli devam | Kilit + `< 0,01 ML` | `PASS` |
| (c) `S3` `32×32` Blanker Ölü Kanal | `%5` (`51 / 1.024`) ölü demet | `%95,0` aktif demet verimi | `128` yedek halka üzerine `51/51` sıfır-çakışmalı eşleme; **`%100,0`** verim | `%100,0` | `PASS` |
| (d) `³¹P` Hiperfine Termal Kayma | `±350 Hz` hat kayması | `350 Hz` detuning hatası | `Q1616BOEDCore` ile **`4,20 ms`** içinde **`29,52 Hz`** artık hatayla yeniden kilit | `< 5,0 ms` ve `< 100 Hz` | `PASS` |

---

## 5. Ön-Kayıtlı `CQ1–CQ7` Karar Özeti ve Güvenlik/Taşınabilirlik Denetimi

| Kriter | Offline (`{Model}`) | Bulut QPU Proxy (`ibm_marrakesh`, Silikon-Dışı) | Kısa Dayanak |
| :--- | :---: | :---: | :--- |
| `CQ1_CELLISA40_OPCODES_AND_OPENQASM3` | `PASS` | `PASS` | `20` v4.0 / `17` v3.5 uyumlu opcode; Heron `cz` ve Eagle `ecr` `16/16` üniter & `16-dt` geçer |
| `CQ2_IBM_REST_BRIDGE_AND_SUBGRAPH_SELECTOR` | `PASS` | `PASS` | Saf `requests` IAM+REST v1 (`0` `qiskit`), `[2,3,4,5,6]` optimal 5Q zincir, 4-format çözücü |
| `CQ3_C1_DD_AND_BELL_TOMOGRAPHY` | `PASS` | `PASS` | Canlı XY4 `0,9280 >` Bare `0,3325` (`+59,5 pp`); canlı Bell `F = 0,9733 >= 0,85` |
| `CQ4_C2_REP3_SYNDROME_SUPPRESSION` | `PASS` | `PASS` | Canlı `p_L_decoded = 0,00378` (`7,83×` < `0,5 × 0,02962`); `p_L_postsel = 0,0000` (`%91,0` tutma) |
| `CQ5_C3_Q16_BOED_RAMSEY_PARITY` | `PASS` | `PASS` (donanım kayması notlu) | Canlı `Q16` vs `FP64 = 1,6 Hz < 0,5 kHz`, `3 <= 5` nokta, `blind-8pt` farkı `0,373 kHz` (`q2` `-4,52 kHz` gerçek kayma) |
| `CQ6_AUTO_RECAL_4_FAULT_MODES` | `PASS` | — (`M0` model) | 4/4 arıza senaryosu otonom olarak spesifikasyon içinde kurtarıldı |
| `CQ7_SECURITY_PORTABILITY_AND_TESTS` | `PASS` | `PASS` | `0` API anahtarı/CRN/Bearer sızıntısı, `0` hardcoded kullanıcı yolu, `0` GFM hatası, tüm `pytest` %100 geçer |

---

## 6. Çalıştırma Komutları

```bash
# Çevrimdışı doğrulama ve birleşik exp145.json üretimi
python3 -B experiments/exp145_cloud_qpu_ibm_validation/run_exp145_offline.py

# Canlı IBM Quantum Platform 2026 QPU koşusu (kimlik bilgileri yalnızca ortam değişkeninden okunur)
IBM_QUANTUM_TOKEN="<TOKEN>" IBM_QUANTUM_INSTANCE="<CRN>" \
  python3 -B experiments/exp145_cloud_qpu_ibm_validation/run_ibm_live_qpu.py --shots 4096

# 2400x1400 4-panelli grafik üretimi (Cairo)
/usr/bin/python3 -B experiments/exp145_cloud_qpu_ibm_validation/plot_exp145.py

# Test paketi
python3 -B -m pytest -p no:cacheprovider -v tests/test_exp145.py
```
