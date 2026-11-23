# Exp128 (`v4.0`) — Parça-Düzeyi BOM Uzlaştırması, 100.000 Örneklemli Korelasyonlu Monte Carlo Bütçe Tavanı & `20 mK` vs `1 K` EVPI Analizi

**Tarih:** 2026-11-23 *(`v4.0` senkronu: `BOM_DETAILED.csv` `159` parça, `M3 v4.0 = $4.609.600`, `RFQ-01..RFQ-07`)*  
**Kayıtlı Tahminler:** `results/exp128_bom_sensitivity/predictions_exp128.json` (ilk simülasyondan önce kilitlendi — değiştirilmedi)  
**Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Gerçek tedarikçi fiyat teklifi ve laboratuvar ölçümü yoktur. Tüm USD sayıları `Exp114` halka açık liste çapalarına (`{Liste-Çapası}`), `Exp114` `$720/birim` sınıf kalibrasyonuna (`{Model-Kalibrasyon-Exp114}`) veya açıkça etiketlenmiş mühendislik varsayımlarına (`{Varsayım}`) dayanır. Kanonik `BOM.csv` dosyasına kesinlikle dokunulmamıştır (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` doğrulandı).

---

## 1. Ön-Kayıtlı Hükümler (`CU1–CU6`, `v4.0` Üzerinde Dürüst Skorlama)

| Hüküm | Kural (`predictions_exp128.json`) | Ölçülen Sonuç (`exp128.json` `v4.0`) | Karar |
|---|---|---|---|
| **CU1 `bom_integrity`** | `BOM.csv` SHA-256 değişmez, `Exp121/122` baz kapısı `<10⁻⁹`, `BOM_DETAILED.csv ≥120` parça & `40/40` kanonik ID + deltalar, uzlaştırma hatası `<10⁻⁶` | SHA-256 birebir; `NL55-B = 0,56029503 / 2159,0004`; **`159` parça** (`40/40` + `S1.5/S1.6/S5.5/S6.9/S6.10`); `v3.0 $4,190M + v4.0 $420k = $4,610M`; köprü hatası **`$0,00`** | **PASS** |
| **CU2 `bom_cap_safety`** | Model A (`N=100.000`): `P(BOM > $50M) < 0,001` ve `BOM P95 < $15M` | `P(BOM > $50M) = 0,00001` (`1/100.000`), `BOM P95 = $11,83M` (`P50 = $5,50M`) | **PASS** |
| **CU3 `program_soft_hard_cap`** | Model A stokastik `M_prog` (`×3–×10`, `P50=5,48×`): `P(Program > $100M) < %5` ve `P(Program > $50M) < %30` | `P(Program > $100M) = %3,38`, `P(Program > $50M) = %21,62` (`P50 = $30,87M`, `P95 = $87,75M`) | **PASS** |
| **CU4 `bc_wall_dominance`** | İlk-3 sürücü (`S6.6 + S6.8 + S2`) BOM varyans payı `≥ %50` **VE** RFQ nominal kapsamı `≥ %75` | İlk-3 varyans payı **`%84,7`** ✓, `7-RFQ` MC varyans kapsamı **`%92,6`** ✓, ancak `7-RFQ` **nominal kapsamı `%72,9 < %75`** (`−2,1` puan; kalan `%27,1` dağınık COTS/yardımcı parça) | **FAIL** *(kıl payı)* |
| **CU5 `evpi_20mk_vindication`** | `N_mach=1`, `C_RD=$2,0M`, `p_succ=0,50` için `1 K` AR-GE `ENV < 0` ve başa-baş `N_be ≥ 4` makine | `E[ΔC_hw] = $665,7k/makine`, `ENV(1) = −$1,67M`, başa-baş **`N_be = 6,01` makine** (`EVPI@1 = $0`) | **PASS** |
| **CU6 `mc_convergence`** | `50k` vs `100k` yarı-bölümde `ΔP50 ≤ %1,0`, `ΔP95 ≤ %1,0` ve `SE(P>100M) < 0,001` | `ΔP50 = %0,388` ✓, `ΔP95 = %0,012` ✓, `SE(P>100M) = 0,00057` ✓ | **PASS** |

> **Başarı Kuralı (`CU1 ∧ CU2 ∧ CU6`):** **`PASS`** (`5/6` ön-kayıtlı hüküm PASS; `CU4` ise `7-RFQ` nominal payının `%72,9 < %75` çıkması nedeniyle dürüstçe `FAIL` olarak korunmuştur).

---

## 2. Kanonik `Exp122` → `M3 v3.0` → `M3 v4.0` (`159` Parça) Uzlaştırması & `M1` vs `M3`

- **Kanonik Kapı:** `NL55-B` = `0,560295033350 / 2159,00039876329`; `NL163` merkez = `3.515,617u = $2.531.244,37 @ $720/u`; `CT1` köşesi = `$13.072.987,48`; `CT2 (×10)` = `$25.312.443,66` — tümü `0,00` sapmayla yeniden üretildi.
- **Birebir Çapa Koruması:** `BOM_DETAILED.csv v4.0` içinde `S6.6-01..06` (`56` okuma zinciri × `$12.150` = **`$680.400`**) ve `S6.8-01..04` (`20 mK` DR = **`$720.000`**) `Exp114/122` ile tam olarak eşleşir.
- **Mühendislik Delta Köprüsü (`$2.531.244` → `v3.0 $4.189.600` → `v4.0 $4.609.600`, net `+$2.078.356`, hata `$0,00`):**
  1. `S2` MEMS sabit maske/DRIE/TSV/wafer-bonding NRE: **`+$764.867`**
  2. **`v4.0` Yükseltme Paketi (`Exp130/131/132/133/134`, `13` HW parça):** **`+$420.000`** (`S6.10` `M4` veri yolu `$245k` + `S5.5` flaş-tavlama `$95k` + `S6.9` `PT420` ayrıştırma `$68k` + `S7.1-04` BOED GPU `$12k`; `Exp134` ile `$0,00` fark)
  3. `COTS / UHV / PT420 / EMI / S7` gerçek katalog çapa uyumu: **`+$285.769`**
  4. `Exp125` `1,50 T / ≤0,40 T` aktif karşı-sargılı mıknatıs + `Nb` kalkan + `9000`-ch `NbTiN` rezonatörler: **`+$261.000`**
  5. `S9` kalibrasyon yongaları, 1 yıllık gaz/katot sarfı & yedek MEMS/LNA kiti: **`+$148.000`**
  6. `Exp124` `10→5 keV` `Arch-B` yavaşlatma lensi + `HDA-HiRes` (`0,453 eV`) + `PH₃` gaz kabini/scrubber: **`+$133.600`**
  7. `Exp127` kilitli `100 K / 1,2 µs / 1 GΩ` (`342 e⁻, η=0,99936`) `16×8` `LTC6268` IBIC ön-uç: **`+$65.119`**
- **`M1 v4.0` vs `M3 v4.0` Ölçeklenmesi:** Tek-demet laboratuvar prototipi **`M1 v4.0` = `$2.336.270`** nominal (`$1,36M–$4,21M`; `M3 v4.0`'ın **`%50,7`'si**; `PT420` ayrıştırma `S6.9`, kompakt `S5.5` flaş ve BOED GPU dahil, `M4` veri yolu `S6.10` M3/M4'te).

---

## 3. 100.000 Örneklemli Monte Carlo Bütçe Tavanı Sonuçları (`v4.0`, `$50M` / `$100M`)

| Model / Senaryo (`N = 100.000`, `seed = 2026128`, `150` Fiyatlı Parça) | Ortalama | `P10` | `P50` | `P90` | `P95` | `P99` | `P(> $50M)` *(Gerekçe)* | `P(> $100M)` *(Sert Aşım)* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Model A — Saf BOM (`B/C` şoksuz, `NL=163`)** | `$5,17M` | `$3,45M` | `$4,96M` | `$7,16M` | `$7,97M` | `$9,79M` | `%0,00` | `%0,00` |
| **Model A — M3 `v4.0` BOM (`NL 110–163` + `%20` C-şoku)** | `$6,22M` | `$3,66M` | **`$5,50M`** | `$9,59M` | `$11,83M` | `$17,35M` | **`%0,00`** (`1e-5`) | **`%0,00`** |
| **Model A — Program Sabit `×3`** | `$18,67M` | `$10,99M` | `$16,50M` | `$28,77M` | `$35,49M` | `$52,04M` | `%1,22` | `%0,02` |
| **Model A — Program Stokastik (`×3–×10`, `P50=5,48×`)** | `$38,05M` | `$14,69M` | **`$30,87M`** | `$68,67M` | `$87,75M` | `$141,71M` | **`%21,62`** | **`%3,38`** *(±%0,06)* |
| **Model A — Program Sabit `×10` (Üst Varsayım)** | `$62,24M` | `$36,65M` | `$55,00M` | `$95,92M` | `$118,31M` | `$173,47M` | `%61,22` | `%8,76` |
| **Model B — Kanonik `Exp122` (`$190–$1600/u`) + `v4.0` Deltalar (BOM)** | `$7,65M` | `$2,86M` | **`$5,49M`** | `$13,48M` | `$18,90M` | `$41,04M` | `%0,64` | `%0,06` |
| **Model B — Kanonik + Deltalar (Program Stokastik)** | `$46,70M` | `$12,41M` | **`$30,83M`** | `$89,62M` | `$128,96M` | `$276,98M` | `%26,83` | `%8,15` |

- **Üçlü Çapraz Doğrulama:** `Model A` (`150`-boyutlu Cholesky kopula, `P50 = $5,50M / $30,87M`), `Model B` (kanonik `Exp122` + deltalar, `P50 = $5,49M / $30,83M`) ve bağımsız `Exp134` (`50k` MC `seed=2026134`, `P50 = $5,49M / $30,96M`, `P>100M = %3,19`) **`%0,3` içinde birebir örtüşmektedir**.

---

## 4. Tornado Duyarlılığı & 7-RFQ Varyans Kapsamı (`v4.0`)

| Sıra | Maliyet Sürücüsü (`BOM_DETAILED v4.0`, Model A) | Sürücü `P50` | BOM Varyans Payı | Spearman `ρ_S` | Koşullu BOM Ort. (`P10 → P90`) | Salınım (`Δ`) |
|---:|---|---:|---:|---:|---:|---:|
| **1** | **`S6.6` Okuma Zinciri (`56–82×`, `B/C` Duvarı)** | `$1.062k` | **`%73,38`** | **`0,886`** | `$3,46M → $12,62M` | **`$9,16M`** |
| **2** | **`S2.1–2.3` MEMS Kafa & Fab NRE** | `$686k` | **`%6,01`** | `0,549` | `$4,38M → $8,82M` | `$4,44M` |
| **3** | **`S6.8` Seyreltme Kriyostatı (`20 mK` DR)** | `$738k` | **`%5,29`** | `0,636` | `$3,99M → $9,33M` | `$5,33M` |
| **4** | **`v4.0` Paketi (`M4 + S5.5 + PT420 + BOED`)** | `$441k` | **`%3,42`** | `0,725` | `$3,75M → $9,79M` | `$6,04M` |
| **5** | `S1` Kaynak + Kolon + Süzgeç + `PH₃` (`Exp124`) | `$434k` | `%2,19` | `0,487` | `$4,50M → $8,42M` | `$3,92M` |
| **6** | `S6` Diğer (`PT420`/MW/RF/SET) | `$266k` | `%2,07` | `0,699` | `$3,82M → $9,74M` | `$5,91M` |
| **7** | `S6.3` `1,50 T / ≤0,40 T` Mıknatıs (`Exp125`) | `$191k` | `%1,46` | `0,633` | `$3,99M → $9,36M` | `$5,36M` |
| 8–10 | `S5` (`%1,20`), `S3` (`%1,20`), `S4` (`%1,12`) | `$235k–$262k` | `%3,52` top. | `0,43–0,45` | `$4,61M → $8,22M` | `~$3,5M` |

- **Program Seviyesi İlk-3 Sürücü:** Program çarpanı (`×3–×10`, `ρ=0,764`, salınım `$63,78M`), `S6.6` `B/C` duvarı (`ρ=0,536`, salınım `$55,63M`) ve `v4.0` paketi (`ρ=0,426`, salınım `$36,40M`).
- **7-RFQ Stratejik Etkisi (`RFQ_SPECIFICATIONS.md`):** Yedi tedarikçi paketi (`RFQ-01..RFQ-07`, `70` parça) nominal `M3 v4.0` donanımının **`%72,9`'unu (`$3,359M`)**, ancak toplam BOM MC varyansının **`%92,6`'sını** kapsar (`RFQ-01..06`: `%64,0` nom, `%89,2` var.).

---

## 5. `20 mK` Baz (`Exp121`) vs. `1 K` Sıcak-Okuma AR-GE EVPI & Başa-Baş Analizi

`S6.8` `20 mK` seyreltme kademesinden (`$720k` nom, MC ort. **`$786,6k`**) `1 K` kapalı-çevrim kademesine (`$110k` nom, MC ort. **`$120,9k`**) geçişin makine başına beklenen donanım tasarrufu **`E[ΔC_hw] = $665.683`** (`$665,7k`; medyan **`$619,6k`**).

| `1 K` AR-GE Bedeli (`C_RD`) | Başarı Olasılığı (`p_succ`) | Başa-Baş (`N_be` Donanım) | Başa-Baş (`N_be` `2×` Entegrasyon) | `N=1` (`M1/M3`) `ENV` / `EVPI` | `N=5` Filo `ENV` / `EVPI` | `N=10` Filo `ENV` / `EVPI` |
|---:|---:|---:|---:|---:|---:|---:|
| `$0,5M` | `%50` | `1,50` | `0,75` | `−$0,17M` / `$82,8k` | `+$1,16M` / `$250,0k` | `+$2,83M` / `$250,0k` |
| `$1,0M` | `%50` | `3,00` | `1,50` | `−$0,67M` / `$0` | `+$0,66M` / `$500,0k` | `+$2,33M` / `$500,0k` |
| **`$2,0M` (`CU5`)** | **`%50`** | **`6,01`** | **`3,00`** | **`−$1,67M` / `$0`** | `−$0,34M` / **`$664,2k`** | `+$1,33M` / `$1.000,0k` |
| `$2,0M` | `%25` | `12,02` | `6,01` | `−$1,83M` / `$0` | `−$1,17M` / `$332,1k` | `−$0,34M` / `$1.164,2k` |
| `$5,0M` | `%50` | `15,02` | `7,51` | `−$4,67M` / `$0` | `−$3,34M` / `$0` | `−$1,67M` / `$828,4k` |

**Karar-Teorik Sonuç:**
1. **İlk makine (`M1`/`M3`, `N=1`) için `Exp121` (`20 mK` DR baz) kararı kesin biçimde optimaldir:** `$2,0M` AR-GE harcaması tek makinede `$666k` tasarrufu aşar (`ENV = −$1,67M`, `EVPI = $0`).
2. **`1 K` sıcak-okuma AR-GE'si ancak çok-makineli filo (`N ≥ 6` donanım) kararı verildiğinde başa-baş olur** (`N=5` karar eşiğinde `EVPI = $664k`).
3. **Buna karşılık `RFQ-01..RFQ-07` tekliflerini göndermek neredeyse sıfır maliyetle `$4,49M`'lik `B/C` duvarı aşım riskini (`%92,6` BOM varyansı) çözer.**

---

## 6. Üretilen Artefaktlar (`v4.0`)
- `research/atom_lithography_machine/BOM_DETAILED.csv` (`159` parça: `145` `v3.0` + `14` `v4.0`)
- `research/atom_lithography_machine/BOM_ENGINEERING.md` (`v4.0`)
- `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md` (`RFQ-01..RFQ-07`)
- `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `run_exp128.py`, `plot_exp128.py`
- `results/exp128_bom_sensitivity/predictions_exp128.json`, `exp128.json`, `summary_exp128.md`
- `results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png`, `fig_exp128_m1_vs_m3_cost.png`
- `tests/test_bom_detailed.py`
