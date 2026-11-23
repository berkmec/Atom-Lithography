# Exp135 (H153) — Uçtan Uca `v4.0` Tam Makine Dijital İkizi Raporu (`Exp124`–`Exp134` + Canlı Kontrol Yığını)

- **Deney / Hipotez:** `exp135_v4_digital_twin` / `H153`
- **Tarih:** 2026-11-23
- **Epistemik Etiket:** `{Model}` / `{Sayısal-Simülasyon}` — **`no_lab_measurement = true`**
- **Genel Karar:** **7/7 Ön-Kayıtlı Tahmin `PASS`** (`success_rule_met = true`, çalışma süresi `9.15 s`)
- **Birincil Veri Bağlantısı:** `Exp124`–`Exp134` arasındaki tüm `11` birincil JSON defteri çalışma zamanında `Path(__file__).resolve()` ile okunmuş ve her birinin `SHA-256` özeti `v4_digital_twin_cert.json` içine kilitlenmiştir.

---

## 1. Yönetici Özeti (`v3.0` → `v4.0` Birleşik Kazanım Tablosu)

`Exp135`, Dalga-1 boyunca üretilen tüm fizik ve mühendislik katmanlarını (`Exp124`–`Exp134`) canlı `src/machine_control/` (`v3.0` BOED + `CellISA v3.0`) kontrol yazılımıyla tek bir çapraz-kuplajlı dijital ikizde (`experiments/exp135_v4_digital_twin/digital_twin135.py`) birleştirmiştir:

| Katman / Metrik | `v3.0` Temel Çizgi | `v4.0` Birleşik (`KL %51`) | `v4.0` Risk `R1` (`VOKL-6 HM5962 %33,25`) | `v4.0` En-Kötü (`VOKL-6 norm %4,75`) | Kazanım / Hüküm |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **L1 Yerleştirme (`15 ms` / `10 ms`)** | `3,716 / 3,674 nm` | **`3,620 / 3,578 nm`** | `3,620 / 3,578 nm` | `3,620 / 3,578 nm` | `<= 3,80 nm` (`CFG1` rijit `2.077 nm` RED!) |
| **L2 IBIC × Flaş-Tavlama Sağkalım** | `%99,936` (tavlamasız) | **`%99,914`** (`η=0,99936 × f_act=0,99978`) | `%99,914` | `%99,914` | Toplam banyo-dışı kayıp yalnız `%0,086` |
| **L4 BOED Ort. Süre (`Factory` / `0-blank`)** | `1.000,0 ms` | **`41,72 / 45,16 ms`** | **`29,87 / 34,51 ms`** | **`10,83 / 17,43 ms`** | Verim düştükçe BOED daha da hızlanır! |
| **L4 Net Verim (`1024 @ 15 ms`)** | `1,973 × 10⁸ / gün` | **`1,502 × 10⁹ / gün`** (`7,61×`) | **`9,794 × 10⁸ / gün`** (`4,96×` v3-KL) | `1,399 × 10⁸ / gün` (`7,61×` v3-norm) | 3 rejimde de **YAZMA-SINIRLI** (`$0` HW) |
| **L4 Net Verim (`1024 @ 10 ms`)** | `1,973 × 10⁸ / gün` | **`2,253 × 10⁹ / gün`** (`11,42×`) | **`1,469 × 10⁹ / gün`** (`7,44×` v3-KL) | `2,099 × 10⁸ / gün` | 3 rejimde de **YAZMA-SINIRLI** |
| **L5 Kuantum & Veri Yolu (`Exp126/131`)** | `50 Ω` CPW `0,791` | **`Q_32D(N=32) = 0,965`**, **`3 kΩ NbTiN = 0,966`** | `10–15 kHz` GRAPE zorunlu (`CE7`) | `10–15 kHz` GRAPE zorunlu | `D0 <= 7,76×10⁻⁹`, `Bell 0,950 / GHZ4 0,940` |
| **L6 `M4` `L=11` FT `%99` İçin `N_cand*`** | `N_cand = 6` (`KL`) | **`N_cand* = 6`** (`Y_FT = %99,24`) | **`N_cand* = 11`** (`N=6`: **`%3,12` çöküş!**) | **`N_cand* = 86` (KIRMIZI ÇİZGİ)** | **`f=%2` `HM5962` (`%54,5`) → `N_cand* = 6` geri döner!** |
| **L7 Makine Maliyeti (`15 ms` / `10 ms`)** | `$52,88 µUSD/reg` | **`$7,33` (`-%86,2`) / `$4,88` (`-%90,8`)** | **`$11,24` (`-%78,8`) / `$7,49`** | `$78,64 µUSD/reg` (`v3`: `$567,8`) | 5y Fab TCO `$15,23M → $16,07M` (`+%5,5`) |
| **L7 `d=17` Mantıksal Kübit (`1/p_B` / `M4`)** | `$0,0598 / $0,1831` | **`$0,0083 / $0,0254`** | **`$0,0195 / $0,0713`** (`N=11`) | `$0,955 / $3,902` (`N=86`) | `P(BOM > $50M) = %0,00`, `P(Prog > $100M) = %3,19` |

---

## 2. Ön-Kayıtlı Karar Tablosu (`predictions_exp135.json` → `7/7 PASS`)

| Tahmin ID | Ön-Kayıtlı Kriter | Ölçülen Sonuç (`exp135.json`) | Karar |
| :--- | :--- | :--- | :---: |
| `DT1_PLACEMENT_BUDGET_V4` | `v4.0 < 3,65 nm` (`15 ms`), `< 3,60 nm` (`10 ms`), `CFG1 > 2.000 nm`, `η × f_act >= 0,999` | `3,6201 nm` (`15 ms`), `3,5776 nm` (`10 ms`), `CFG1 = 2.076,97 nm`, `η × f_act = 0,999140` | **PASS** |
| `DT2_BOED_WRITE_CEILING_ACROSS_R1` | `t_BOED` verim düştükçe azalır; 3 `R1` rejiminde de yazma-sınırlı; `KL >= 1,50e9/g`, `HM5962 >= 9,5e8/g` | `41,72 → 29,87 → 10,83 ms`; 3/3 yazma-sınırlı; `KL = 1,502e9/g`, `HM5962 = 9,794e8/g` | **PASS** |
| `DT3_VOKL6_M4_PERCOLATION_PENALTY` | `HM5962` `N_cand=6` `<%10` çöküş, `N_cand* ∈ [10, 12]`; `norm > 50`; `f=%2` → `N_cand* = 6` | `N=6: %3,12`, **`N_cand* = 11`** (`%99,74`); `norm: 86`; `f=%2: 6` (`%99,92`) | **PASS** |
| `DT4_UNIT_ECONOMICS_AND_BUDGET_CAP` | Maliyet düşüşü `>=%80`, `KL <= $8`, `HM5962 <= $12`, `d=17 < $0,01 / $0,025`, `P(>100M) < %5` | `-%86,15`, `$7,33 / $11,24 µUSD`, `d=17 = $0,0083 / $0,0195`, `P(>50M BOM)=%0,00`, `P(>100M)=%3,19` | **PASS** |
| `DT5_EXP126_QUANTUM_AND_BUS_BRIDGE` | `Q_32D_α2 >= 0,94`, `Bell >= 0,94`, `GHZ4 >= 0,93`, `D0 <= 1e-8`, `3 kΩ >= 0,96`, `50 Ω < 0,80` | `0,9433`, `0,9501`, `0,9401`, `7,76×10⁻⁹`, `0,9655`, `0,7908` | **PASS** |
| `DT6_LIVE_4X4_WAFER_DIGITAL_TWIN_CERT` | Canlı `4×4` yönlendirme `F_joint >= 0,95`, `min_CZ >= 0,98`, `SHA-256` ana sertifika doğrulaması | `F_joint = 0,983448`, `min_CZ = 0,988923`, `SHA-256 = feffc1d4ba2b0698...` (`True`) | **PASS** |
| `DT7_PORTABILITY_AND_REGRESSION` | Sıfır hardcoded konak yolu, `0` GFM hatası, `%100` pytest | `portability_hardcoded_hits = []`, `0` GFM hatası, `6/6 test_exp135.py PASS` | **PASS** |

---

## 3. Kritik Çapraz-Katman Keşifleri

### 3.1 `Exp131 × Exp129` Çarpışması: Risk `R1` Altında `M4` 2B Yüzey Kodu Perkolasyonu (`N_cand*`)
`Exp131` kanonik `KL` (`p_B = %51,0`) altında `Δz_cap* = 8 nm` (`p_ff = %95,20`) ile birleşik tek-yuva verimini `p_M4 = 0,48552` olarak hesaplamış ve `L = 11` (`121` düğüm, `<= 6` ölü düğüm `%5` FT tavanı) için `N_cand = 6` aday yuva ile **`Y_FT = %99,24`** vermişti.

`Exp129` Risk `R1` aşağı-yönlü verim zarfı (`VOKL-6 HM5962`, `p_B = %33,25`) bu tablo üzerine binince `p_M4 = 0,3325 × 0,9520 = 0,31654` değerine geriler. Kesin binom hesabı ve `N_mc = 2.000` 2B kare-kafes perkolasyon Monte Carlo doğrulaması şunu göstermiştir:

| Rejim (`p_B` × `p_ff = 0,952`) | `p_M4` | `Y_FT(L=11, N=6)` | `Y_FT(L=11, N=9)` | `Y_FT(L=11, N=10)` | `Y_FT(L=11, N=11)` | `N_cand*` (`L=5 / L=11 / L=21`, `>=%99`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Canonical `KL` (`f = %1,0`) | `0,48552` | **`%99,24`** | `%100,00` | `%100,00` | `%100,00` | `8 /` **`6`** `/ 6` |
| **`VOKL-6 HM5962` (`f = %1,0`, Risk `R1`)** | **`0,31654`** | **`%3,12` (ÇÖKÜŞ!)** | `%89,92` | `%98,11` | **`%99,74`** | `14 /` **`11`** `/ 10` |
| **`VOKL-6 HM5962` (`f = %2,0` İzotop Kaldıracı)** | **`0,51884`** | **`%99,92`** | `%100,00` | `%100,00` | `%100,00` | `7 /` **`6`** `/ 5` |
| `VOKL-6 norm` (`f = %1,0`, En-Kötü Zemin) | `0,04522` | `%0,00` | `%0,00` | `%0,00` | `%0,00` | `111 /` **`86`** `/ 76` (**Kırmızı Çizgi**) |

- **Mimari Sonuç:** `VOKL-6 HM5962` laboratuvarda doğrulanırsa mevcut `N_cand = 6` kavite-bus düğüm mimarisi `%3,12` yonga verimine çöker. İki somut mühendislik kurtarma yolu vardır: (1) düğüm başına aday yuva sayısını `N_cand = 6 → 11` seviyesine çıkarmak (`1,83×` kavite ayak izi, `d=17` maliyeti `$0,0713` hâlâ `v3.0`'ın `$0,1831`'inin altında!), veya (2) izotop zenginliğini `f = %1,0 → %2,0` yapmak (ancak `Exp126` `α=1` DD kapısının `f = %2,0` altında `N_total` sınırlarını yeniden doğrulamak koşuluyla). `VOKL-6 norm` (`N_cand* = 86`) ise fiziksel kırmızı çizgidir ve ilk kriyostat `ENDOR` deneyinde elenmesi gereken `#1` go/no-go kapısıdır.

### 3.2 Uyarlamalı BOED Yastıklama Etkisi (`Exp132 × Exp129`)
Sabit `1,0 s` taramalı `v3.0` makinesi `VOKL-6 HM5962` (`%33,25`) veriminde `1,286 × 10⁸` yazmaç/gün düzeyine çökerken, `v4.0` BOED spektrometresi daha fazla kalabalık yuvayı `14,58 ms`'de erken iptal ederek ortalama tarama süresini **`41,72 ms → 29,87 ms`**'ye indirir (sıfır-boşluklu muhafazakâr sınırda bile `34,51 ms`). Böylece makine tüm `Exp129` rejimlerinde **tamamen yazma-sınırlı** kalır ve `VOKL-6 HM5962` altında bile `v3.0`'ın kanonik `KL` veriminin **`4,96×` (`15 ms`) / `7,44×` (`10 ms`)** üzerinde üretim yapar.

---

## 4. Canlı `src/machine_control/` Entegrasyon ve `SHA-256` Ana Sertifika (`L8`)

- **Canlı `120`-Yuvalı `Factory` Koşumu:**
  - `v300_KL`: `105` sertifikalı, `1.000,0 ms/deneme`, `1,973 × 10⁸/gün`.
  - `v400_KL`: `111` sertifikalı, canlı ortalama **`45,23 ms/deneme`**, `89` erken iptal, `1,503 × 10⁹/gün`.
  - `v400_VOKL6_HM5962`: `87` sertifikalı, canlı ortalama **`31,66 ms/deneme`**, `168` erken iptal, `9,796 × 10⁸/gün`.
- **Canlı Tek-Hücre `AtomCellProgrammer` (`ALM-000000`):** `Bell` nominal `0,995878` (köşe min `0,977378`), `GHZ4` nominal `0,996797`.
- **Canlı `4×4` Heterojen Wafer (`BayesianSpectrometer` → `MultiCellProgrammer`):** `8` çalışan / `8` ölü yuva, ortalama BOED taraması `40,82 ms`, yönlendirilen 4 hücre `DT4-{R0C0, R0C1, R0C2, R1C0}` (`3` adet `1`-hop `NbTiN` `BUS_CZ`), **`F_joint = 0,983448`**, **`min_bus_cz = 0,988923`**, `Exp126` 32D köprüsü bağlı (`all_clear_5kHz_gate = True`).
- **Kriptografik `v4.0` Dijital İkiz Ana Sertifikası (`results/exp135_v4_digital_twin/v4_digital_twin_cert.json`):**
  - `SHA-256 = feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57` (diskten geri okuma ve tahrifat testi `test_exp135.py` içinde doğrulandı).

---

## 5. Kapsam Dışı / Epistemik Sınırlar
- `no_lab_measurement = true`: Tüm 8 katman `Exp124`–`Exp134` sayısal/kuramsal modellerine dayanır; gerçek laboratuvar `ENDOR` hiperince haritalaması (`Risk R1`) ve kriyostat içi flaş-tavlama/IBIC deneyi yapılmamıştır.
- `Exp134` Rejim II yonga-zemin uyarısı geçerlidir: ham `²⁸Si` yonga maliyeti (`$12k/yonga`) yoğun fablarda toplam çip maliyetinin `%92`'sine kadar taban oluşturur; yukarıdaki `L7` rakamları Rejim I kararlı-durum makine amortisman + OPEX birim maliyetidir.
