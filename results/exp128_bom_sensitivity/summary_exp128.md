# Exp128 (`v5.0`) — Parça-Düzeyi BOM Uzlaştırması, 100.000 Örneklemli Korelasyonlu Monte Carlo Bütçe Tavanı & `20 mK` vs `1 K` EVPI Analizi

**Tarih:** 2026-11-23 *(`v5.0` senkronu: `BOM_DETAILED.csv` `167` parça, `M3 v5.0 = $5.247.800`, `RFQ-01..RFQ-08`, çift-sayım kredisi `−$86k`, kütle doğrulaması `S5.6=22,4 kg` & `S6.5/S6.11=19,27 kg`)*  
**Kayıtlı Tahminler:** `results/exp128_bom_sensitivity/predictions_exp128.json` (ilk simülasyondan önce kilitlendi — değiştirilmedi)  
**Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Gerçek tedarikçi fiyat teklifi ve laboratuvar ölçümü yoktur. Tüm USD sayıları `Exp114/140` halka açık liste çapalarına (`{Liste-Çapası}`), `Exp114` `$720/birim` sınıf kalibrasyonuna (`{Model-Kalibrasyon-Exp114}`) veya açıkça etiketlenmiş mühendislik varsayımlarına (`{Varsayım}`) dayanır. Kanonik `BOM.csv` dosyasına kesinlikle dokunulmamıştır (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`).

---

## 1. Ön-Kayıtlı Hükümler (`CU1–CU6`, `v5.0` Üzerinde **`6/6 PASS`**)

| Hüküm | Kural (`predictions_exp128.json`) | Ölçülen Sonuç (`exp128.json` `v5.0`) | Karar |
|---|---|---|---|
| **CU1 `bom_integrity`** | `BOM.csv` SHA-256 değişmez, `Exp121/122` kapısı `<10⁻⁹`, `BOM_DETAILED ≥120` parça & `40/40` kanonik ID + deltalar, uzlaştırma hatası `<10⁻⁶` | SHA-256 birebir; `NL55-B = 0,56029503 / 2159,0004`; **`167` parça** (`40/40` + `S1.5/S1.6/S5.5/S5.6/S6.9/S6.10/S6.11`); `v4.0 $4,610M + $724,2k − $86k = $5,248M`; köprü & kütle hatası **`$0,00` / `0,000 kg`** | **PASS** |
| **CU2 `bom_cap_safety`** | Model A (`N=100.000`): `P(BOM > $50M) < 0,001` ve `BOM P95 < $15M` | `P(BOM > $50M) = 0,00002` (`2/100.000`), `BOM P95 = $12,52M` (`P50 = $6,15M`) | **PASS** |
| **CU3 `program_soft_hard_cap`** | Model A stokastik `M_prog` (`×3–×10`, `P50=5,48×`): `P(Program > $100M) < %5` ve `P(Program > $50M) < %30` | `P(Program > $100M) = %4,23` (`±%0,06`), `P(Program > $50M) = %26,72` (`P50 = $34,59M`, `P95 = $94,75M`) | **PASS** |
| **CU4 `bc_wall_dominance`** | İlk-3 sürücü (`S6.6 + S6.8 + S2`) BOM varyans payı `≥ %50` **VE** RFQ nominal kapsamı `≥ %75` | İlk-3 varyans payı **`%82,0`** ✓, `8-RFQ` MC varyans kapsamı **`%92,6`** ✓, **`8-RFQ` nominal kapsamı `%76,4 ≥ %75`** ✓ (`RFQ-08` stratejik donanımı kapsayarak eşiği geçti!) | **PASS** |
| **CU5 `evpi_20mk_vindication`** | `N_mach=1`, `C_RD=$2,0M`, `p_succ=0,50` için `1 K` AR-GE `ENV < 0` ve başa-baş `N_be ≥ 4` makine | `E[ΔC_hw] = $662,7k/makine`, `ENV(1) = −$1,67M`, başa-baş **`N_be = 6,04` makine** (`EVPI@1 = $0`) | **PASS** |
| **CU6 `mc_convergence`** | `50k` vs `100k` yarı-bölümde `ΔP50 ≤ %1,0`, `ΔP95 ≤ %1,0` ve `SE(P>100M) < 0,001` | `ΔP50 = %0,042` ✓, `ΔP95 = %0,584` ✓, `SE(P>100M) = 0,00064` ✓ | **PASS** |

> **Genel Başarı Kuralı (`CU1 ∧ CU2 ∧ CU6`) & Dürüst Risk Notu:** `6/6` ön-kayıtlı hüküm **`PASS`** vermiştir. Ancak tam `1.024`-hücreli `M3 v5.0` (`$5,25M`) Program CAPEX sert sınır riskini `%3,38`'den **`%4,23`'e** (`%5` eşiğine `0,77` puan marj) ve **5-yıllık FOAK TCO** (Program + `$2,5M` temizoda + 5y OPEX) kuyruğunu **`%5,91`'e** (`P50 = $43,53M, P95 = $105,30M`) taşır. Aşamalı `256`-hücreli Pilot (`$4,79M`) seçeneği `$100M` marjını tamamen geri kazanır.

---

## 2. Kanonik `Exp122` → `M3 v3.0` → `M3 v4.0` → `M3 v5.0` (`167` Parça) Köprüsü & Çift-Sayım Denetimi

- **Kanonik Kapı & Çapalar:** `BOM.csv` `40/40` satır (`$2.531.244,37 @ $720/u`), `S6.6-01..06 = $680.400`, `S6.8-01..04 = $720.000` — tümü `$0,00` sapmayla korundu.
- **Kanonik Kimlik Koruması (`S6.5` Çakışması Yok):** Kanonik `BOM.csv` `S6.5` = `RF/ENDOR hattı` (`S6.5-01..03 = $22k`) dokunulmadan korundu; `Exp140` `s65_hardware_spec.json` (`19,27 kg`, `$629,2k`) `BOM_DETAILED.csv`'de **`S6.11-01..04`** altında birebir eşlendi.
- **Tam `$0,00` Köprü:**
  - `Exp122` (`$2.531.244`) + `v3.0` Deltaları (`+$1.658.356`) = **`M3 v3.0 = $4.189.600`** (`145` parça).
  - `+ v4.0` Paketi (`+$420.000`) = **`M3 v4.0 = $4.609.600`** (`159` parça).
  - `+ v5.0` Brüt Yeni Donanım (**`+$724.200`**, `41,67 kg`): `S5.6` In-Situ `²⁸Si` UHV MBE (`+$95.000`, `22,40 kg`) + `S6.11` [`Exp140 S6.5`] `1.024`-hücre Cryo-MUX (`+$629.200`, `19,27 kg` = `11,50 kg` raf + `7,77 kg` soğuk).
  - **`− v4.0 → v5.0` Çift-Sayım Önleme Kredisi (`−$86.000`):** `S6.10-02` harici 10-yonga `8 nm` kaplama (`−$54.000`), `S6.10-04` `5 GHz` RF sürücü yarısı (`−$20.000`), `S7.1-04` ayrık BOED GPU (`−$12.000`).
  - **`= M3 v5.0` Tam `1.024`-Hücre Toplamı:** **`$5.247.800`** nominal (`$3.039.400–$9.525.900`, net `+$638.200`, hata **`$0,00`**).
  - **`M3 v5.0` `256`-Hücre Pilot:** **`$4.790.400`** | **`M1 v5.0` Prototip:** **`$2.466.120`** (`%47,0` of `M3 v5.0`).

---

## 3. 100.000 Örneklemli Monte Carlo Bütçe Tavanı & 5-Yıllık Fab/FOAK TCO Bağlamı (`v5.0`)

| Model / Senaryo (`N = 100.000`, `seed = 2026128`, `156` Fiyatlı Parça) | Ortalama | `P10` | `P50` | `P90` | `P95` | `P99` | `P(> $50M)` | `P(> $100M)` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Model A — Saf BOM (`B/C` şoksuz, `NL=163`)** | `$5,82M` | `$3,96M` | `$5,58M` | `$7,96M` | `$8,82M` | `$10,74M` | `%0,00` | `%0,00` |
| **Model A — M3 `v5.0` BOM (`NL 110–163` + `%20` C-şoku)** | `$6,87M` | `$4,19M` | **`$6,15M`** | `$10,33M` | `$12,52M` | `$18,01M` | **`%0,00`** (`2e-5`) | **`%0,00`** |
| **Model A — Program Sabit `×3`** | `$20,60M` | `$12,56M` | `$18,46M` | `$30,98M` | `$37,57M` | `$54,02M` | `%1,48` | `%0,02` |
| **Model A — Program Stokastik (`×3–×10`, `P50=5,48×`)** | `$41,97M` | `$16,61M` | **`$34,59M`** | `$75,26M` | `$94,75M` | `$150,17M` | **`%26,72`** | **`%4,23`** *(±%0,06)* |
| **Model A — Program Sabit `×10` (Üst Varsayım)** | `$68,65M` | `$41,86M` | `$61,53M` | `$103,27M` | `$125,23M` | `$180,07M` | `%74,74` | `%11,18` |
| **Model B — Kanonik `Exp122` + `v5.0` Deltalar (Program Stok.)** | `$50,95M` | `$14,43M` | **`$34,81M`** | `$96,47M` | `$134,09M` | `$282,00M` | `%31,55` | `%9,32` |
| **`v5.0` Ticari Fab Aracı `N=1` 5-Yıllık TCO (yongasız)** | — | `$13,09M` | **`$17,23M`** | `$24,97M` | `$28,84M` | — | `%0,00` | `%0,00` |
| **`v5.0` FOAK Program 5-Yıllık TCO (Program+Tesis+5y OPEX)** | — | `$24,90M` | **`$43,53M`** | `$85,30M` | **`$105,30M`** | — | `%38,77` | **`%5,91`** *(uyarı)* |

- **Çapraz Doğrulama:** `Model A` (`156`-boyutlu Cholesky kopula, `P50 = $34,59M`) ile `Model B` (kanonik `Exp122` + deltalar, `P50 = $34,81M`) **`%0,6` içinde** uyuşur.

---

## 4. Tornado Duyarlılığı, `8-RFQ` Varyans Kapsamı & `20 mK` vs `1 K` EVPI (`v5.0`)

| Sıra | Maliyet Sürücüsü (`BOM_DETAILED v5.0`, Model A) | Sürücü `P50` | BOM Varyans Payı | Spearman `ρ_S` | Koşullu BOM Ort. (`P10 → P90`) | Salınım (`Δ`) |
|---:|---|---:|---:|---:|---:|---:|
| **1** | **`S6.6` Okuma Zinciri (`56–82×`, `B/C` Duvarı)** | `$1.058k` | **`%70,62`** | **`0,884`** | `$3,97M → $13,29M` | **`$9,32M`** |
| **2** | **`S2.1–2.3` MEMS Kafa & Fab NRE** | `$685k` | **`%6,04`** | `0,551` | `$4,91M → $9,64M` | `$4,74M` |
| **3** | **`S6.8` Seyreltme Kriyostatı (`20 mK` DR)** | `$735k` | **`%5,30`** | `0,646` | `$4,50M → $10,20M` | `$5,70M` |
| **4** | **`v5.0` Paketi (`S5.6` MBE + `S6.5/S6.11` TWPA/FPGA)** | `$733k` | **`%3,37`** | `0,712` | `$4,29M → $10,55M` | `$6,26M` |
| **5** | **`v4.0` Paketi (`M4` + `S5.5` + `PT420` net)** | `$350k` | **`%2,69`** | `0,728` | `$4,26M → $10,62M` | `$6,36M` |
| 6–10 | `S1` (`%2,18`), `S6` Diğer (`%2,09`), `S6.3` (`%1,48`), `S5` (`%1,23`), `S3` (`%1,23`) | `$190k–$433k` | `%8,21` top. | `0,44–0,71` | `$4,30M → $10,57M` | `$3,8–6,3M` |

- **`8-RFQ` Kapsamı (`RFQ-01..RFQ-08`, `78` parça):** Nominal **`%76,4` (`$4,009M`)**, MC varyansı **`%92,6`** (`RFQ-08` tek başına `%13,8` nom / `%3,4` var.).
- **`20 mK` vs `1 K` EVPI (`CU5 PASS`):** `E[ΔC_hw] = $662,7k/makine` (`20 mK` ort. `$783,4k` vs `1 K` `$120,7k`, medyan `$617,9k`); `N=1, C_RD=$2M, p=%50` için `ENV = −$1,67M`, `EVPI = $0`, başa-baş **`N_be = 6,04` makine** (`N=5` `EVPI = $656,7k`, `N=10` `EVPI = $1.000k`).

---

## 5. Üretilen Artefaktlar (`v5.0`)
- `research/atom_lithography_machine/BOM_DETAILED.csv` (`167` parça: `145` `v3.0` + `14` `v4.0` + `8` `v5.0`)
- `research/atom_lithography_machine/BOM_ENGINEERING.md` (`v5.0`)
- `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md` (`RFQ-01..RFQ-08`)
- `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `run_exp128.py`, `plot_exp128.py`
- `results/exp128_bom_sensitivity/predictions_exp128.json`, `exp128.json`, `summary_exp128.md`
- `results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png`, `fig_exp128_m1_vs_m3_cost.png`
- `tests/test_bom_detailed.py`
