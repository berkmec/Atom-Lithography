# Exp128 (`v6.0`) — Parça-Düzeyi Modüler BOM Uzlaştırması, 100.000 Örneklemli Korelasyonlu Monte Carlo Bütçe Tavanı & `20 mK` vs `1 K` EVPI Analizi

**Tarih:** 2026-11-23 *(`v6.0` modüler senkronu: `BOM_DETAILED.csv` `174` parça = `167` `M3 v5.0 Base` [`$5.247.800`] + `4` `Option-Q` [`+$168.000`, `9,20 kg`] + `3` `Option-HPC` [`+$132.000`, `64,00 kg`] = **`$5.547.800`**; `RFQ-01..RFQ-09`; `$0,00` köprü & `0,000 kg` kütle eşleşmesi [`CAD v6.0 = 1.108,14 kg`])*  
**Kayıtlı Tahminler:** `results/exp128_bom_sensitivity/predictions_exp128.json` (ilk simülasyondan önce kilitlendi — değiştirilmedi)  
**Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Gerçek tedarikçi fiyat teklifi ve laboratuvar ölçümü yoktur. Tüm USD sayıları `Exp114/140/143` halka açık liste çapalarına (`{Liste-Çapası}`), `Exp114` `$720/birim` sınıf kalibrasyonuna (`{Model-Kalibrasyon-Exp114}`) veya açıkça etiketlenmiş mühendislik varsayımlarına (`{Varsayım}`) dayanır. Kanonik `BOM.csv` dosyasına kesinlikle dokunulmamıştır (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2`).

---

## 1. Ön-Kayıtlı Hükümler (`CU1–CU6`, `v6.0 Full` & `M3 Base` Üzerinde **`6/6 PASS`**)

| Hüküm | Kural (`predictions_exp128.json`) | Ölçülen Sonuç (`exp128.json` `v6.0`, `N = 100.000`) | Karar |
|---|---|---|---|
| **CU1 `bom_integrity`** | `BOM.csv` SHA-256 değişmez, `Exp121/122` kapısı `<10⁻⁹`, `BOM_DETAILED ≥120` parça & `40/40` kanonik ID + deltalar, uzlaştırma hatası `<10⁻⁶` | SHA-256 birebir; `NL55-B = 0,56029503 / 2159,0004`; **`174` parça** (`40/40` + `10` delta ebeveyn); `Base $5,248M + OptQ $168k + OptHPC $132k = $5,548M`; köprü & kütle hatası **`$0,00` / `0,000 kg`** | **PASS** |
| **CU2 `bom_cap_safety`** | Model A (`N=100.000`): `P(BOM > $50M) < 0,001` ve `BOM P95 < $15M` | `P(BOM > $50M) = 0,00003` (`3/100.000`), `BOM P95 = $12,98M` (`P50 = $6,46M`) | **PASS** |
| **CU3 `program_soft_hard_cap`** | Model A stokastik `M_prog` (`×3–×10`, `P50=5,48×`): `P(Program > $100M) < %5` ve `P(Program > $50M) < %30` | **`M3 v5.0 Base` (`$5,25M`):** `P>100M = %4,37`, `P>50M = %26,77` ✓; **`M3 v6.0 Full` (`$5,55M`):** **`P>100M = %4,92 ± %0,07`** *(95% GA `[%4,79, %5,05]`)*, `P>50M = %29,34` (`P50 = $36,25M`, `P95 = $99,48M`) ✓ | **PASS** *(sınırda — aşağıya bkz.)* |
| **CU4 `bc_wall_dominance`** | İlk-3 sürücü (`S6.6 + S6.8 + S2`) BOM varyans payı `≥ %50` **VE** RFQ nominal kapsamı `≥ %75` | İlk-3 varyans payı **`%81,3`** ✓, `9-RFQ` MC varyans kapsamı **`%92,6`** ✓, **`9-RFQ` nominal kapsamı `%77,7 ≥ %75`** ✓ (`85` parça, `$4,309M`) | **PASS** |
| **CU5 `evpi_20mk_vindication`** | `N_mach=1`, `C_RD=$2,0M`, `p_succ=0,50` için `1 K` AR-GE `ENV < 0` ve başa-baş `N_be ≥ 4` makine | `E[ΔC_hw] = $664,2k/makine`, `ENV(1) = −$1,67M`, başa-baş **`N_be = 6,02` makine** (`EVPI@1 = $0`) | **PASS** |
| **CU6 `mc_convergence`** | `50k` vs `100k` yarı-bölümde `ΔP50 ≤ %1,0`, `ΔP95 ≤ %1,0` ve `SE(P>100M) < 0,001` | `ΔP50 = %0,013` ✓, `ΔP95 = %0,549` ✓, `SE(P>100M) = 0,00068` ✓ | **PASS** |

> **Dürüst Kuyruk-Riski & Modüler Ayrım Beyanı (`M3 Base` vs `M3 v6.0 Full`):** `6/6` ön-kayıtlı hüküm hem `M3 v5.0 Base` hem `M3 v6.0 Full` için **`PASS`** vermiştir. Ancak tam donanımlı **`M3 v6.0 Full` (`$5,548M`)** nokta tahmini `P(Program > $100M) = %4,92 ± %0,07` (`%5` sınırına yalnız `0,08` yüzde puan / `~1,2σ` mesafede; `%95` güven aralığı `[%4,79, %5,05]` `%5` eşiğine dokunmaktadır) ve **5-yıllık FOAK TCO** (`Program + $2,5M` temizoda `+ 5y OPEX`) **`%6,90`** (`P50 = $45,34M, P95 = $110,1M`) ile `%5` üzerindedir. Buna karşılık **`M3 v5.0 Base` (`$5,248M`)** `P(Program > $100M) = %4,37` (`%95` GA `[%4,24, %4,50]`; `v5.0` bağımsız çekimde `%4,23`) ile `%5`'in belirgin altındadır. Bu nedenle `Option-Q` (`+$168k`) ve `Option-HPC` (`+$132k`) çekirdek `M3 Base` faturasından kesinlikle ayrılmış, sahada takılabilir modüler eklentiler olarak konumlandırılmıştır.

---

## 2. Kanonik `Exp122` → `M3 v5.0 Base` → `M3 v6.0 Full` (`174` Parça) Köprüsü & Çift-Sayım Denetimi

- **Kanonik Kapı & Çapalar:** `BOM.csv` `40/40` satır (`$2.531.244,37 @ $720/u`), `S6.6-01..06 = $680.400`, `S6.8-01..04 = $720.000`, `M1 Base = $2.466.120` — tümü `$0,00` sapmayla korundu.
- **Kimlik Çakışması Önleme (`S1.6`, `S6.5`, `S9.1` Korundu):**
  - `Exp140 S6.5` (`19,27 kg`, `$629,2k`) → `S6.11-01..04` (`BOM.csv` `S6.5 = RF/ENDOR` korundu).
  - `Exp142 S1.6-01` (`4,80 kg`, `$68k`) → **`S1.7-01`** (`BOM_DETAILED` `S1.6 = PH₃/SiF₄` korundu).
  - `Exp142 S9.1-01..03` (`4,40 kg`, `$100k`) → **`S9.4-01..03`** (`BOM.csv` `S9.1 = kalibrasyon yongaları` korundu).
  - `Exp143 S9.HPC-01..03` (`64,00 kg`, `$132k`) → **`S9.HPC-01..03`** (yeni alt-grup, sıfır çakışma).
- **Tam `$0,00` Köprü & `0,000 kg` Kütle Eşleşmesi:**
  - `Exp122` (`$2.531.244`) → `M3 v3.0` (`$4.189.600`) → `M3 v4.0` (`$4.609.600`) → **`M3 v5.0 Base` (`$5.247.800`, `167` parça, `1.034,94 kg`)** → `+ Option-Q` (`+$168.000`, `+9,20 kg`) + `+ Option-HPC` (`+$132.000`, `+64,00 kg`) = **`M3 v6.0 Full = $5.547.800`** (`174` parça, **`1.108,14 kg`**, köprü hatası **`$0,00`**, kütle hatası **`0,000 kg`**).

---

## 3. Modüler 4-Yapılandırma 100.000 Örneklemli Monte Carlo Karşılaştırması (Ortak Rastgele Sayılar)

| Yapılandırma (`N = 100.000`, `seed = 2026128`) | Nominal HW | BOM `P50` | Program Stok. `P50` | Program `P95` | `P(Prog > $50M)` | `P(Prog > $100M)` | Fab `N=1` 5y TCO `P50` | FOAK 5y TCO `P50` (`P>100M`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`M3 v5.0 Base` (`167` parça)** | `$5,248M` | `$6,15M` | `$34,50M` | `$95,90M` | `%26,77` | **`%4,37`** | `$17,23M` | `$43,45M` (`%6,21`) |
| **`M3 v6.0 +Option-HPC` (`170` parça)** | `$5,380M` | `$6,28M` | `$35,26M` | `$97,36M` | `%27,90` | **`%4,60`** | `$17,47M` | `$44,28M` (`%6,47`) |
| **`M3 v6.0 +Option-Q` (`171` parça)** | `$5,416M` | `$6,32M` | `$35,49M` | `$97,86M` | `%28,21` | **`%4,67`** | `$17,54M` | `$44,50M` (`%6,59`) |
| **`M3 v6.0 Full` (`174` parça, OptQ+OptHPC)** | **`$5,548M`** | **`$6,46M`** | **`$36,25M`** | **`$99,48M`** | **`%29,34`** | **`%4,92`** *(±%0,07)* | **`$17,78M`** | **`$45,34M`** (`%6,90`) |

### 3.1 Tam `M3 v6.0 Full` Dağılım Tablosu (`Model A` vs `Model B`)

| Model / Senaryo (`N = 100.000`, `163` Fiyatlı Parça) | Ortalama | `P10` | `P50` | `P90` | `P95` | `P99` | `P(> $50M)` | `P(> $100M)` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Model A — Saf BOM (`B/C` şoksuz, `NL=163`)** | `$6,13M` | `$4,23M` | `$5,90M` | `$8,32M` | `$9,19M` | `$11,12M` | `%0,00` | `%0,00` |
| **Model A — M3 `v6.0 Full` BOM (`NL 110–163` + `%20` C-şoku)** | `$7,19M` | `$4,46M` | **`$6,46M`** | `$10,64M` | `$12,98M` | `$18,58M` | **`%0,00`** (`3e-5`) | **`%0,00`** |
| **Model A — Program Sabit `×3`** | `$21,56M` | `$13,37M` | `$19,38M` | `$31,92M` | `$38,93M` | `$55,75M` | `%1,72` | `%0,02` |
| **Model A — Program Stokastik (`×3–×10`, `P50=5,48×`)** | `$44,03M` | `$17,56M` | **`$36,25M`** | `$78,86M` | `$99,48M` | `$155,93M` | **`%29,34`** | **`%4,92`** *(±%0,07)* |
| **Model A — Program Sabit `×10` (Üst Varsayım)** | `$71,85M` | `$44,58M` | `$64,61M` | `$106,40M` | `$129,75M` | `$185,83M` | `%80,77` | `%12,43` |
| **Model B — Kanonik `Exp122` + `v6.0` Deltalar (Program Stok.)** | `$53,13M` | `$15,29M` | **`$36,93M`** | `$99,49M` | `$139,52M` | `$290,33M` | `%34,14` | `%9,91` |

- **Çapraz Doğrulama:** `Model A` (`163`-boyutlu Cholesky kopula, `P50 = $36,25M`) ile `Model B` (kanonik `Exp122` + deltalar, `P50 = $36,93M`) **`%1,9` içinde** uyuşur.

---

## 4. Tornado Duyarlılığı, `9-RFQ` Varyans Kapsamı & `20 mK` vs `1 K` EVPI (`v6.0`)

| Sıra | Maliyet Sürücüsü (`BOM_DETAILED v6.0`, Model A) | Sürücü `P50` | BOM Varyans Payı | Spearman `ρ_S` | Koşullu BOM Ort. (`P10 → P90`) | Salınım (`Δ`) |
|---:|---|---:|---:|---:|---:|---:|
| **1** | **`S6.6` Okuma Zinciri (`56–82×`, `B/C` Duvarı)** | `$1.061k` | **`%70,03`** | **`0,879`** | `$4,25M → $13,70M` | **`$9,45M`** |
| **2** | **`S2.1–2.3` MEMS Kafa & Fab NRE** | `$686k` | **`%5,97`** | `0,553` | `$5,21M → $9,99M` | `$4,78M` |
| **3** | **`S6.8` Seyreltme Kriyostatı (`20 mK` DR)** | `$736k` | **`%5,28`** | `0,650` | `$4,80M → $10,58M` | `$5,78M` |
| **4** | **`v5.0` Paketi (`S5.6` MBE + `S6.5/S6.11` TWPA/FPGA)** | `$734k` | **`%3,34`** | `0,715` | `$4,59M → $10,89M` | `$6,30M` |
| **5** | **`v4.0` Paketi (`M4` + `S5.5` + `PT420` net)** | `$351k` | **`%2,68`** | `0,730` | `$4,56M → $11,00M` | `$6,44M` |
| 6–14 | `S1`, `S6` Diğer, `S6.3`, `S3`, `S5`, `S4`, `S7`, `S9` Yedek, `S2` Diğer | `$119k–$434k` | `%11,88` top. | `0,44–0,72` | `$4,58M → $11,02M` | `$3,8–6,4M` |
| **15** | **`v6.0` `Option-Q` (`qRAM` + `S1-Multi`, `9,20 kg`)** | `$171k` | **`%0,50`** | `0,515` | `$5,24M → $9,67M` | `$4,44M` |
| **16** | **`v6.0` `Option-HPC` (`100G` RDMA Dekoder, `64,00 kg`)** | `$133k` | **`%0,31`** | `0,376` | `$5,74M → $8,94M` | `$3,20M` |

- **`9-RFQ` Kapsamı (`RFQ-01..RFQ-09`, `85` parça):** Nominal **`%77,7` (`$4,309M`)**, MC varyansı **`%92,6`** (`RFQ-09` tek başına `%5,4` nom / `%0,8` var.).
- **`20 mK` vs `1 K` EVPI (`CU5 PASS`):** `E[ΔC_hw] = $664,2k/makine` (`20 mK` ort. `$784,8k` vs `1 K` `$120,6k`, medyan `$619,6k`); `N=1, C_RD=$2M, p=%50` için `ENV = −$1,67M`, `EVPI = $0`, başa-baş **`N_be = 6,02` makine** (`N=5` `EVPI = $660,6k`, `N=10` `EVPI = $1.000k`).

---

## 5. Üretilen Artefaktlar (`v6.0`)
- `research/atom_lithography_machine/BOM_DETAILED.csv` (`174` parça: `167` `M3 v5.0 Base` + `7` `v6.0` Modüler Opsiyon)
- `research/atom_lithography_machine/BOM_ENGINEERING.md` (`v6.0`)
- `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md` (`RFQ-01..RFQ-09`)
- `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `run_exp128.py`, `plot_exp128.py`
- `results/exp128_bom_sensitivity/predictions_exp128.json`, `exp128.json`, `summary_exp128.md`
- `results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png`, `fig_exp128_m1_vs_m3_cost.png`
- `tests/test_bom_detailed.py`
