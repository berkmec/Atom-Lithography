# Exp141 (H159) — Master `v5.0` Uçtan-Uca Hata-Toleranslı Dijital İkiz, Wafer-Ekonomi `CX4` Kapanışı ve Kriptografik `v5` Sertifikası Raporu

- **Deney / Hipotez:** `exp141_v5_digital_twin` / `H159`
- **Sürüm:** `v5.0`
- **Tarih:** 2026-11-23
- **Epistemik Etiket:** `{Model}` / `{Sayısal-Simülasyon}` / `{Varsayım}` / `{Liste-Çapası}` — **`no_lab_measurement = true`**, **`no_supplier_quotes = true`**
- **Genel Karar:** **8/8 Ön-Kayıtlı Tahmin `PASS`** (`DT5_1..DT5_8`, `success_rule_met = true`, çalışma süresi `1,73 s`)
- **Tam 64-Hex Kriptografik `v5.0` Ana Sertifika `SHA-256` Özeti (`results/exp141_v5_digital_twin/v5_digital_twin_cert.json`):**
  `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`

---

## 1. Yönetici Özeti (`v3.0 → v4.0 → v5.0` Master Evrim Tablosu)

`Exp141`, tüm `17` birincil deney defterini (`Exp124`–`Exp140`), `CAD v5.0` (`189` parça, `1.034,94 kg`, `0/17.766` çakışma, `32/32` boşluk), `BOM_DETAILED v5.0` (`167` parça, `M3 = $5.247.800`, `$0,00` uzlaştırma hatası), `wafer_econ141.py` wafer/mantıksal-kübit ekonomisini ve canlı `src/machine_control/` (`Q16.16` BOED-FPGA + `CellISA v3.5`) kontrol yığınını tek bir uçtan-uca hata-toleranslı dijital ikizde birleştirmiştir:

| Sistem Katmanı / Metrik | `v3.0` Temel Çizgi | `v4.0` Dijital İkiz (`Exp135`) | **`v5.0` Master FT Dijital İkiz (`Exp141`)** | Mühendislik Hükmü |
| :--- | :---: | :---: | :---: | :--- |
| **Yerleştirme Bütçesi (`15 ms` / `10 ms`)** | `3,716 / 3,674 nm` | `3,620 nm` (gizli TED: **`3,963 / 3,995 nm` FAIL!**) | **`3,631 / 3,588 nm`** (`1530 K`, `Exp139: 3,665 nm`) | `{311}` küme temizliği (`%99,99`) → `<= 3,80 nm` **PASS** |
| **Hücre Verimi & Kusurlu Kafes (`Exp136/138`)** | `KL %51,0` | `VOKL-6 %33,25` (`N_cand*=11`) | **`f*=%1,5 + 2 MV/m: %77,50`**, `d_eff/d = %99,5` (`N=6`) | Atomistik `sp³d⁵s*` + Stark ile `N_cand=6` kurtarıldı |
| **Flip-Flop Kaplama & Yük Gürültüsü (`Exp139`)** | Yok (`%24,5`) | `8 nm` MBE (`%95,2`, `S_ε = 1,0`) | **Rota C (`1530 K + 8 nm + FG`): `%97,70`, `S_ε = 0,390`** | `2,57×` yük gürültüsü baskılaması (`S5.6`, `%0` akış kaybı) |
| **M4 Kavite-Bus `CZ` (`Exp137`)** | `50 Ω` CPW `0,791` | Çıplak `P1` (`F_Bell = 0,845`, `Λ = 0,00`) | **`P4 Echo CZ`: `F_Bell = 0,9893` (`Q=5e5: 0,9949`)** | `1/f` yük gürültüsü kırıldı; `F_avg = %99,26` |
| **BOED-FPGA & Mux Okuma (`Exp140`)** | `1.000 ms` FP64 | `41,0 ms` FP64 (`8.960` ch) | **`Q16.16` `2,336 µs/adım` (`abs(ΔRMS)=0,018 Hz`)**, **`N_mux*=32` (`F_RO=%99,61`)** | `1.024` hücre `PT420`'de kapanır; tavan `2.887` hücre/kriyostat |
| **Kontrol Yazılımı (`src/machine_control/`)** | `CellISA v2.0` (`10` op) | `CellISA v3.0` (`14` op) | **`CellISA v3.5` (`17` op: `ECHO_CZ`, `MUX_READOUT`, `SYNDROME_CYCLE`)** | Canlı `ECHO_CZ = 0,9818` (`+20,3 pp`), `T_cyc = 2,62 µs` |
| **Yüzey Kodu Hata Bastırma (`Exp138`, `d=3..11`)** | Eşik üstü | `v4 P1`: `Λ = 0,00` (**FAIL**) | **`D2`: `Λ = 1,399`** (`Q=5e5, S=0,25`); **`D3` (`p_2q=%0,5`): `Λ = 2,520`** | Gerçek üstel hata bastırma (`p_2q,th = %1,60`) |
| **Yoğun Fab `10k`-Çip Maliyeti (`CX4`)** | `$3,012` (`W1`) | `$2,603` (`Exp134 v4.0-5x`, `-%13,7`, `CX4 FAIL`) | `W1`: `$2,576` (`-%14,5`, `FAIL`) → **`W2`: `$0,616` (`-%79,5`)**; **`W3`: `$0,442` (`-%85,3`, `PASS`)** | **`Exp134 CX4` SİLİKON DUVARI KIRILDI!** |
| **`CAD` / `BOM` (`M3` Nominal)** | `143` / `145` (`$4,19M`) | `170` / `159` (`$4,61M`) | **`189` (`1.034,9 kg`, `0` çakışma, `32/32`) / `167` (`$5,248M`)** | `$0,00` BOM uzlaştırma, `19/19` `SHA-256` kilitli |

---

## 2. Ön-Kayıtlı Karar Tablosu (`predictions_exp141.json` → `8/8 PASS`)

| Tahmin ID | Ön-Kayıtlı Kriter | Ölçülen Sonuç (`exp141.json`) | Karar |
| :--- | :--- | :--- | :---: |
| `DT5_1_LEDGER_CAD_BOM_INTEGRITY` | `17` deney + `CAD v5` (`189`, `0` çakışma, `32/32`) + `BOM v5` (`167`, `$5,2478M`, `$0` hata) | `17` deney + `CAD` (`189`, `1.034,94 kg`, `0/17.766`, `32/32`) + `BOM` (`167`, `$5.247.800`, `$0,00`) | **PASS** |
| `DT5_2_V5_PLACEMENT_BUDGET_CLOSURE` | `v5` `1530 K` `<= 3,80 nm` (`v4` gizli TED `> 3,80 nm` düzeltilir) | `v4` gizli TED: `3,9634 / 3,9951 nm` (FAIL) → **`v5`: `3,6307 / 3,5883 nm`** (`Exp139: 3,6653 nm`) | **PASS** |
| `DT5_3_ATOMISTIC_MBE_ECHO_MUX_CHAIN` | `f*=%1,5+2MV/m >=%75`, `d_eff/d>=%99`, `p_ff>=%97`, `S_ε<=0,40`, `P4>=0,985`, `N_mux*=32` | `%77,50`, `d_eff/d=%99,5`, `p_ff=%97,70`, `S_ε=0,3897`, `P4=0,9893/0,9949`, `N_mux*=32 (0,9961)` | **PASS** |
| `DT5_4_LIVE_CELLISA35_AND_Q16_FPGA` | Canlı `abs(ΔRMS_Q16) < 1 Hz`, `ECHO_CZ >= 0,98`, `T_cyc <= 3 µs`, `17` opcode `SHA-256` | `abs(ΔRMS) = 0,0183 Hz` (`2,336 µs`), `Bare=0,7791 → ECHO_CZ=0,9818`, `T_cyc=2,620 µs`, `SHA-256 OK` | **PASS** |
| `DT5_5_SURFACE_CODE_FT_THRESHOLD_CLOSURE` | `v4 P1 Λ<1`, `D2 Λ>=1,35`, `D3 Λ>=2,2`, `100L (10⁻⁹)` kriyostat düşüşü `>= 6×` | `P1 Λ=0,00`, **`D2 Λ=1,399`**, **`D3 Λ=2,520`**, `679 → 100` kriyostat (**`6,79×`**) | **PASS** |
| `DT5_6_WAFER_CX4_SILICON_WALL_BROKEN` | `W1 CX4=False`; `W2 >= %75`, `W3 >= %80` düşüş + aynı-wafer `CX4=True` | `W1: -%14,5 (FAIL)`; **`W2: -%79,5` (`-%41,4` aynı-w)**; **`W3: -%85,3` (`-%50,0` aynı-w)** | **PASS** |
| `DT5_7_LOGICAL_QUBIT_ECONOMICS_D2_AND_D3` | `$/L_fab(W3, 10⁻⁹) < $10 (D2) / < $2 (D3)` ve `D2/D3` sistem oranı `>= 5×` | `D2`: `$5,20/L_fab`, `$14,94M/L_sys`; **`D3`: `$0,73/L_fab`, `$2,76M/L_sys`** (**`5,414×`**) | **PASS** |
| `DT5_8_CRYPTO_V5_CERT_PORTABILITY_AND_TESTS` | Tam 64-hex `SHA-256` doğrulama, `0` hardcoded yol, `0` GFM hatası, tüm testler `PASS` | `64`-hex `SHA-256` disk & özet eşleşti, `0` yol ihlali, `0` GFM hatası, tam depo regresyon `PASS` | **PASS** |

---

## 3. Gerçek `$/Mantıksal Kübit` Ekonomisi: Silikon Fab Payı (`$/L_fab`) vs `100L` Dağıtılmış Kriyostat Sistemi (`$/L_sys`)

Aşağıdaki tablo `wafer_econ141.evaluate_logical_qubit_economics()` çıktısının canlı `Exp138` (`D2` birincil `Λ = 1,399` ve `D3` hedef `Λ = 2,520`, `N_cand = 6`) ve `Exp140` (`2.887` hücre/kriyostat tavanı) ile birleştirilmiş dürüst ayrımını gösterir (`Wright b = %85`, amortize fab P50):

| Rejim & Hedef `ε_L` | Uzaklık `d*` | Aktif / Yerleşen Hücre | `100L` Kriyostat (`2.887` Tavan) | `$/L_fab` (`W1` `$12k`) | `$/L_fab` (`W2` `$2,2k`) | `$/L_fab` (`W3` `$3,6k`) | `$/L_sys` (`100L` Amort., Wright) | `$/L_sys` (`100L` Adanmış Fab) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `D2` (`Λ=1,40`) `ε_L = 10⁻⁶` | `59` | `6.961 / 41.766` | `242` | `$10,76` | `$2,57` | **`$1,85`** | `$6.010.332` | `$6.181.890` |
| `D2` (`Λ=1,40`) `ε_L = 10⁻⁹` | `99` | `19.601 / 117.606` | `679` | `$30,30` | `$7,25` | **`$5,20`** | `$14.939.541` | `$15.111.098` |
| `D2` (`Λ=1,40`) `ε_L = 10⁻¹²` | `141` | `39.761 / 238.566` | `1.378` | `$61,46` | `$14,70` | **`$10,54`** | `$28.132.343` | `$28.303.900` |
| **`D3` (`Λ=2,52`) `ε_L = 10⁻⁶`** | **`21`** | `881 / 5.286` | **`34`** (`3 L/kriyo`) | `$1,36` | `$0,33` | **`$0,23`** | **`$1.084.933`** | `$1.256.491` |
| **`D3` (`Λ=2,52`) `ε_L = 10⁻⁹`** | **`37`** | `2.737 / 16.422` | **`100`** (`1 L/kriyo` bölünmez!) | `$4,23` | `$1,01` | **`$0,73`** | **`$2.759.442`** | `$2.930.999` |
| **`D3` (`Λ=2,52`) `ε_L = 10⁻¹²`** | **`51`** | `5.201 / 31.206` | **`181`** | `$8,04` | `$1,92` | **`$1,38`** | **`$4.665.318`** | `$4.836.875` |

> **Temel Sistem Keşfi:** Atom Litografi Makinesi `v5.0` (ince `30 nm` `²⁸Si-on-SOI` `W2/W3` + `Q16.16` BOED) çip üretim maliyetini **`$0,23–$5,20 / mantıksal kübit`** düzeyine indirerek fabrikasyon darboğazını kalıcı biçimde ortadan kaldırmaktadır (toplam dağıtılmış sistem TCO'sunun yalnızca **`%0,0001–%0,0002`**'si!). Çalışma-zamanı hata-toleranslı kuantum bilgisayar maliyetinin `#1` belirleyicisi `20 mK` kriyostat + `S6.5` mikrodalga okuma filosudur: `2`-kübit kapı hatasını `D2` (`%0,92`) → `D3` (`%0,50`) düzeyine düşürmek `100L (10⁻⁹)` filosunu `679 → 100` kriyostata (**`6,79×`**) ve mantıksal kübit başına dağıtılmış TCO'yu `$14,94M → $2,76M` (**`5,41×`**) indirir!

---

## 4. Kriptografik `v5.0` Ana Sertifika ve Kapsam Dışı Sınırlar

- **Tam 64-Hex `SHA-256` Özeti (`results/exp141_v5_digital_twin/v5_digital_twin_cert.json`):**
  `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1`
- **Bağlanan `19` Birincil Artefakt:** `exp124.json`..`exp140.json` (`17` deney), `research/atom_lithography_machine/cad/cad_verification.json` (`CAD v5.0`), `research/atom_lithography_machine/BOM_DETAILED.csv` (`BOM v5.0`) — tamamının `64`-hex `SHA-256` özeti `v5_digital_twin_cert.json["primary_ledger_sha256"]` içinde kayıtlıdır ve `tests/test_exp141.py` tarafından diskten birebir doğrulanır.
- **Epistemik Sınırlar:** `no_lab_measurement = true` ve `no_supplier_quotes = true`. Tüm fiziksel zincirler (`sp³d⁵s*` TB, `1/f` Lindblad `P4`, `d=3..11` MWPM, `1530 K` TED + MBE, `Q16.16` BOED-FPGA, `3 kΩ` `NbTiN` TWPA, `W2/W3` `30 nm` SOI) sayısal model ve mühendislik varsayımlarına dayanır; fiziksel donanım üretimi, kriyostat ENDOR/TWPA ölçümü veya tedarikçi teklifi içermez.
