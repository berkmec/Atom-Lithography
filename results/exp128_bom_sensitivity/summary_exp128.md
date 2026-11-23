# Exp128 (`v7.0`) — Parça-Düzeyi Modüler BOM & Emniyet Uzlaştırması, 100.000 Örneklemli Monte Carlo Bütçe Tavanı & `20 mK` vs `1 K` EVPI Analizi

**Tarih:** 2026-11-23 *(`v7.0` SEMI S2/SIL-3 senkronu: `BOM_DETAILED.csv` `180` parça = `167` `M3 Base` [`$5.247.800`] + `7` `v6.0` Opsiyon [`+$300.000`, `73,20 kg`] + `6` `v7.0` `S7.SAFETY` [`+$145.000`, `355,0 kg` tesis] = **`$5.692.800`**; `RFQ-01..RFQ-10`; `$0,00` köprü & `0,0000 kg` şasi/tesis kütle eşleşmesi)*  
**Kayıtlı Tahminler:** `results/exp128_bom_sensitivity/predictions_exp128.json` (ilk simülasyondan önce kilitlendi — değiştirilmedi)  
**Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Gerçek tedarikçi fiyat teklifi ve laboratuvar ölçümü yoktur. Tüm USD sayıları `Exp114/140/143/150` halka açık liste çapalarına (`{Liste-Çapası}`), `Exp114` `$720/birim` sınıf kalibrasyonuna (`{Model-Kalibrasyon-Exp114}`) veya açıkça etiketlenmiş mühendislik varsayımlarına (`{Varsayım}`) dayanır. Kanonik `BOM.csv` dosyasına kesinlikle dokunulmamıştır (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`).

---

## 1. Ön-Kayıtlı Hükümler (`CU1–CU6`: Genel Başarı `PASS`; `v7 Full` `CU3` Dürüst Sınır Aşımı vs Faz-1 `Base+Safety` `6/6 PASS`)

| Hüküm | Kural (`predictions_exp128.json`) | Ölçülen Sonuç (`exp128.json` `v7.0`, `N = 100.000`) | Karar |
|---|---|---|---|
| **CU1 `bom_integrity`** | `BOM.csv` SHA-256 değişmez, `Exp121/122` kapısı `<10⁻⁹`, `BOM_DETAILED ≥120` parça & `40/40` kanonik ID + deltalar, uzlaştırma hatası `<10⁻⁶` | SHA-256 birebir; `NL55-B = 0,56029503 / 2159,0004`; **`180` parça** (`40/40` + `11` delta ebeveyn); `v6 Full $5,548M + S7.SAFETY $145k = $5,693M`; köprü & kütle hatası **`$0,00` / `0,0000 kg`** | **PASS** |
| **CU2 `bom_cap_safety`** | Model A (`N=100.000`): `P(BOM > $50M) < 0,001` ve `BOM P95 < $15M` | `P(BOM > $50M) = 0,00001` (`1/100.000`), `BOM P95 = $13,08M` (`P50 = $6,62M`) | **PASS** |
| **CU3 `program_soft_hard_cap`** | Model A stokastik `M_prog` (`×3–×10`, `P50=5,48×`): `P(Prog > $100M) < %5` ve `P(Prog > $50M) < %30` | **Faz-1 `Base+Safety` (`$5,393M`):** `P>100M=%4,67 < %5`, `P>50M=%28,11 < %30` (**PASS**); **`M3 Base` (`$5,248M`):** `%4,44 / %26,84` (**PASS**); **`v6 Full` (`$5,548M`):** `%4,95 / %29,38` (**PASS**); **`v7 Full` (`$5,693M`):** **`P>100M=%5,22 ± %0,07`**, **`P>50M=%30,66`** (`P95=$101,49M`) | **FAIL (v7 Full)**; **PASS (Faz-1 Base+Safety)** |
| **CU4 `bc_wall_dominance`** | İlk-3 sürücü (`S6.6 + S6.8 + S2`) BOM varyans payı `≥ %50` **VE** RFQ nominal kapsamı `≥ %75` | İlk-3 varyans payı **`%80,7`** ✓, `10-RFQ` MC varyans kapsamı **`%92,6`** ✓, **`10-RFQ` nominal kapsamı `%78,2 ≥ %75`** ✓ (`91` parça, `$4,454M`) | **PASS** |
| **CU5 `evpi_20mk_vindication`** | `N_mach=1`, `C_RD=$2,0M`, `p_succ=0,50` için `1 K` AR-GE `ENV < 0` ve başa-baş `N_be ≥ 4` makine | `E[ΔC_hw] = $664,9k/makine`, `ENV(1) = −$1,67M`, başa-baş **`N_be = 6,02` makine** (`EVPI@1 = $0`) | **PASS** |
| **CU6 `mc_convergence`** | `50k` vs `100k` yarı-bölümde `ΔP50 ≤ %1,0`, `ΔP95 ≤ %1,0` ve `SE(P>100M) < 0,001` | `ΔP50 = %0,138` ✓, `ΔP95 = %0,530` ✓, `SE(P>100M) = 0,00070` ✓ | **PASS** |

> **Genel Başarı Kuralı (`CU1 ∧ CU2 ∧ CU6 = PASS`) & Dürüst Fazlı Bütçe Stratejisi:** Tek seferde tüm modüller + brüt emniyet paketi birlikte alındığında (**`M3 v7.0 Safety-Certified Full = $5,693M`**), stokastik Program CAPEX kuyruğu `P(Program > $100M) = %5,22 ± %0,07` (`+0,22` puan) ve `P(> $50M) = %30,66` ile ön-kayıtlı `CU3` sınırlarını kıl payı aşar (`FOAK 5y TCO P>100M = %7,25`). Buna karşılık **Faz-1 `M3 Base + Safety` (`$5,393M`, `173` parça — tam `SEMI S2 / ANSI Z136.1 / SIL-3` sertifikalı!)** **`P(Program > $100M) = %4,67 < %5`** ve **`P(> $50M) = %28,11 < %30`** ile **`6/6 CU1–CU6 PASS`** verir! Dolayısıyla bağlayıcı bütçe-tavanı kapanış yolu: **Faz-1 `M3 Base + Safety` (`$5,393M`) → `RFQ-05` (`S6.6 B/C` duvarı) teklif kilidi → Faz-2 `Option-Q` (`+$168k`) & `Option-HPC` (`+$132k`)** modüler kademelemesidir. *(Not: Başlangıç koruma kalemleri `S1.6/S5.5-04/S7.1-03/S7.4-04` [`$76,2k`] ikame kredisi uygulanırsa net `v7 Full` `$5,617M`'a iner; burada muhafazakâr brüt `$5,693M` raporlanmıştır.)*

---

## 2. Kanonik `Exp122` → `M3 Base` → `M3 Base+Safety` → `M3 v7.0 Full` (`180` Parça) & Kütle Eşleşmesi

- **Korunan Sabitler (`$0,00` sapma):** `BOM.csv` SHA-256 değişmedi (`40/40`, `$2.531.244`), `M1 Base = $2.466.120` (`M1 + Safety = $2.611.120`), `M3 v5.0 Base = $5.247.800` (`167` parça), `M3 v6.0 Full = $5.547.800` (`174` parça).
- **Şasi-Üstü vs Tesis Kütle Ayrımı (`0,0000 kg` fark):** `CAD v6.0` şasi-üstü kütlesi **`1.108,137 kg`** (`199` parça) değişmeden korunur; `S7.SAFETY-01..06` (**`355,000 kg`**, `1.090 W`, `0 W` kriyo) harici temizoda zemin emniyet yükü olarak eklenir → toplam tesis yükü **`1.463,137 kg`**.

---

## 3. Modüler 6-Yapılandırma 100.000 Örneklemli Monte Carlo Karşılaştırması (Ortak Rastgele Sayılar)

| Yapılandırma (`N = 100.000`, `seed = 2026128`) | Nominal HW | BOM `P50` | Program Stok. `P50` | Program `P95` | `P(Prog > $50M)` | `P(Prog > $100M)` | Fab `N=1` 5y TCO `P50` | FOAK 5y TCO `P50` (`P>100M`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`M3 v5.0 Base` (`167p`)** | `$5,248M` | `$6,15M` | `$34,62M` | `$96,23M` | `%26,84` | **`%4,44`** *(PASS)* | `$17,23M` | `$43,54M` (`%6,16`) |
| **`M3 Base + Safety` (`173p`, Faz-1)** | **`$5,393M`** | **`$6,31M`** | **`$35,48M`** | **`$97,95M`** | **`%28,11`** | **`%4,67`** *(PASS)* | **`$17,50M`** | **`$44,48M`** (`%6,51`) |
| **`M3 v6.0 +Option-HPC` (`170p`)** | `$5,380M` | `$6,29M` | `$35,38M` | `$97,70M` | `%27,94` | `%4,63` *(PASS)* | `$17,47M` | `$44,37M` (`%6,46`) |
| **`M3 v6.0 +Option-Q` (`171p`)** | `$5,416M` | `$6,33M` | `$35,60M` | `$98,18M` | `%28,29` | `%4,69` *(PASS)* | `$17,54M` | `$44,61M` (`%6,55`) |
| **`M3 v6.0 Full` (`174p`, OptQ+OptHPC)** | `$5,548M` | `$6,46M` | `$36,37M` | `$99,64M` | `%29,38` | **`%4,95`** *(PASS)* | `$17,78M` | `$45,43M` (`%6,87`) |
| **`M3 v7.0 Safety-Certified Full` (`180p`)** | **`$5,693M`** | **`$6,62M`** | **`$37,24M`** | **`$101,49M`** | **`%30,66`** | **`%5,22`** *(±%0,07; FAIL)* | **`$18,05M`** | **`$46,36M`** (`%7,25`) |

### 3.1 Tam `M3 v7.0 Full` Dağılım Tablosu (`Model A` vs `Model B`)

| Model / Senaryo (`N = 100.000`, `169` Fiyatlı Parça) | Ortalama | `P10` | `P50` | `P90` | `P95` | `P99` | `P(> $50M)` | `P(> $100M)` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Model A — Saf BOM (`B/C` şoksuz, `NL=163`)** | `$6,29M` | `$4,36M` | `$6,05M` | `$8,50M` | `$9,41M` | `$11,32M` | `%0,00` | `%0,00` |
| **Model A — M3 `v7.0 Full` BOM (`NL 110–163` + `%20` C-şoku)** | `$7,34M` | `$4,59M` | **`$6,62M`** | `$10,87M` | `$13,08M` | `$18,72M` | **`%0,00`** (`1e-5`) | **`%0,00`** |
| **Model A — Program Sabit `×3`** | `$22,03M` | `$13,78M` | `$19,86M` | `$32,61M` | `$39,25M` | `$56,17M` | `%1,83` | `%0,03` |
| **Model A — Program Stokastik (`×3–×10`, `P50=5,48×`)** | `$45,00M` | `$17,98M` | **`$37,24M`** | `$80,14M` | `$101,49M` | `$158,65M` | **`%30,66`** | **`%5,22`** *(±%0,07)* |
| **Model A — Program Sabit `×10` (Üst Varsayım)** | `$73,44M` | `$45,92M` | `$66,19M` | `$108,71M` | `$130,82M` | `$187,22M` | `%83,34` | `%13,40` |
| **Model B — Kanonik `Exp122` + `v7.0` Deltalar (Program Stok.)** | `$53,90M` | `$15,76M` | **`$37,86M`** | `$100,28M` | `$140,27M` | `$288,84M` | `%34,98` | `%10,06` |

- **Çapraz Doğrulama:** `Model A` (`169`-boyutlu Cholesky kopula, `P50 = $37,24M`) ile `Model B` (`P50 = $37,86M`) **`%1,7` içinde** uyuşur.

---

## 4. Tornado Duyarlılığı, `10-RFQ` Varyans Kapsamı & `20 mK` vs `1 K` EVPI (`v7.0`)

| Sıra | Maliyet Sürücüsü (`BOM_DETAILED v7.0`, Model A) | Sürücü `P50` | BOM Varyans Payı | Spearman `ρ_S` | Koşullu BOM Ort. (`P10 → P90`) | Salınım (`Δ`) |
|---:|---|---:|---:|---:|---:|---:|
| **1** | **`S6.6` Okuma Zinciri (`56–82×`, `B/C` Duvarı)** | `$1.058k` | **`%69,55`** | **`0,876`** | `$4,39M → $13,88M` | **`$9,49M`** |
| **2** | **`S2.1–2.3` MEMS Kafa & Fab NRE** | `$686k` | **`%5,91`** | `0,554` | `$5,32M → $10,10M` | `$4,78M` |
| **3** | **`S6.8` Seyreltme Kriyostatı (`20 mK` DR)** | `$736k` | **`%5,27`** | `0,650` | `$4,89M → $10,74M` | `$5,85M` |
| **4** | **`v5.0` Paketi (`S5.6` MBE + `S6.5/S6.11` TWPA/FPGA)** | `$734k` | **`%3,34`** | `0,716` | `$4,71M → $11,12M` | `$6,41M` |
| **5** | **`v4.0` Paketi (`M4` + `S5.5` + `PT420` net)** | `$351k` | **`%2,67`** | `0,731` | `$4,67M → $11,26M` | `$6,59M` |
| 6–14 | `S1`, `S6` Diğer, `S6.3`, `S5`, `S3`, `S4`, `S7` Kontrol, `S9` Yedek, `S2` Diğer | `$119k–$434k` | `%11,94` top. | `0,44–0,72` | `$4,71M → $11,24M` | `$3,8–6,5M` |
| **15** | **`v6.0` `Option-Q` (`qRAM` + `S1-Multi`, `9,20 kg`)** | `$171k` | **`%0,51`** | `0,517` | `$5,37M → $9,88M` | `$4,50M` |
| **16** | **`v7.0` Emniyet Paketi (`S7.SAFETY` SEMI S2/SIL-3, `355 kg`)** | `$148k` | **`%0,50`** | `0,436` | `$5,67M → $9,47M` | `$3,81M` |
| **17** | **`v6.0` `Option-HPC` (`100G` RDMA Dekoder, `64,00 kg`)** | `$132k` | **`%0,31`** | `0,378` | `$5,86M → $9,11M` | `$3,25M` |

- **`10-RFQ` Kapsamı (`RFQ-01..RFQ-10`, `91` parça):** Nominal **`%78,2` (`$4,454M`)**, MC varyansı **`%92,6`** (`RFQ-10` tek başına `%2,5` nom / `%0,50` var.).
- **`20 mK` vs `1 K` EVPI (`CU5 PASS`):** `E[ΔC_hw] = $664,9k/makine` (`20 mK` ort. `$785,4k` vs `1 K` `$120,6k`, medyan `$619,8k`); `N=1, C_RD=$2M, p=%50` için `ENV = −$1,67M`, `EVPI = $0`, başa-baş **`N_be = 6,02` makine** (`N=5` `EVPI = $662,2k`, `N=10` `EVPI = $1.000k`).

---

## 5. Üretilen Artefaktlar (`v7.0`)
- `research/atom_lithography_machine/BOM_DETAILED.csv` (`180` parça: `167` `M3 Base` + `7` `v6.0` Opsiyon + `6` `v7.0` `S7.SAFETY`)
- `research/atom_lithography_machine/BOM_ENGINEERING.md` (`v7.0`)
- `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md` (`RFQ-01..RFQ-10`)
- `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `run_exp128.py`, `plot_exp128.py`
- `results/exp128_bom_sensitivity/predictions_exp128.json`, `exp128.json`, `summary_exp128.md`
- `results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png`, `fig_exp128_m1_vs_m3_cost.png`
- `tests/test_bom_detailed.py`
