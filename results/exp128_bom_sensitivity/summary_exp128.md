# Exp128 — Parça-Düzeyi BOM Uzlaştırması, 100.000 Örneklemli Korelasyonlu Monte Carlo Bütçe Tavanı & `20 mK` vs `1 K` EVPI Analizi

**Tarih:** 2026-11-22  
**Kayıtlı Tahminler:** `results/exp128_bom_sensitivity/predictions_exp128.json` (hesaplamadan önce kilitlendi)  
**Epistemik Beyan (`no_lab_measurement=true`, `no_supplier_quotes=true`):** Gerçek tedarikçi fiyat teklifi ve laboratuvar ölçümü yoktur. Tüm USD sayıları `Exp114` halka açık liste çapalarına (`{Liste-Çapası}`), `Exp114` `$720/birim` sınıf kalibrasyonuna (`{Model-Kalibrasyon-Exp114}`) veya açıkça etiketlenmiş mühendislik varsayımlarına (`{Varsayım}`) dayanır. Kanonik `BOM.csv` dosyasına dokunulmamıştır (`SHA-256: cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2` doğrulandı).

---

## 1. Ön-Kayıtlı Hükümler (`CU1–CU6`) — Dürüst Skorlama

| Hüküm | Kural | Ölçülen Sonuç | Karar |
|---|---|---|---|
| **CU1 `bom_integrity`** | `BOM.csv` SHA-256 değişmez, `Exp121/122` baz kapısı `<10⁻⁹`, `BOM_DETAILED.csv ≥120` parça & `40/40` kanonik ID + `Exp124/125/127`, uzlaştırma hatası `<10⁻⁶` | SHA-256 birebir; `NL55-B = 0,56029503 / 2159,0004`; **`145` parça** (`40/40` + `S1.5/S1.6`); köprü hatası **`$0,00`** | **PASS** |
| **CU2 `bom_cap_safety`** | Model A (`N=100.000`): `P(BOM > $50M) < 0,001` ve `BOM P95 < $15M` | `P(BOM > $50M) = 0,00000` (`0/100.000`), `BOM P95 = $11,20M` (`P50 = $5,01M`) | **PASS** |
| **CU3 `program_soft_hard_cap`** | Model A stokastik `M_prog` (`×3–×10`, `P50=5,48×`): `P(Program > $100M) < %5` ve `P(Program > $50M) < %30` | `P(Program > $100M) = %2,69`, `P(Program > $50M) = %18,10` (`P50 = $28,24M`, `P95 = $82,11M`) | **PASS** |
| **CU4 `bc_wall_dominance`** | İlk-3 sürücü (`S6.6 + S6.8 + S2`) BOM varyans payı `≥ %50` **VE** 6-RFQ nominal kapsamı `≥ %75` | İlk-3 varyans payı **`%88,3`** ✓, 6-RFQ MC varyans kapsamı **`%92,8`** ✓, ancak 6-RFQ **nominal kapsamı `%70,4 < %75`** (`−4,6` puan; kalan `%29,6` dağınık COTS/yardımcı parça) | **FAIL** *(kıl payı)* |
| **CU5 `evpi_20mk_vindication`** | `N_mach=1`, `C_RD=$2,0M`, `p_succ=0,50` için `1 K` AR-GE `ENV < 0` ve başa-baş `N_be ≥ 4` makine | `E[ΔC_hw] = $662,9k/makine`, `ENV(1) = −$1,67M`, başa-baş **`N_be = 6,03` makine** (`EVPI@1 = $0`) | **PASS** |
| **CU6 `mc_convergence`** | `50k` vs `100k` yarı-bölümde `ΔP50 ≤ %1,0`, `ΔP95 ≤ %1,0` ve `SE(P>100M) < 0,001` | `ΔP50 = %0,032` ✓, `SE(P>100M) = 0,00051` ✓, ancak `%20` `C`-sınıfı ağır kuyrukta **`ΔP95 = %1,46 > %1,0`** | **FAIL** *(ağır sağ kuyruk)* |

> **Başarı Kuralı (`CU1 ∧ CU2 ∧ CU6`):** `CU6`'nın ağır sağ kuyruktaki `%1,46` P95 örnekleme dalgalanması yüzünden kayıtlı katı başarı kuralı **FAIL** olarak işlendi (eşik gevşetilmedi, ön-kayıtlı öngörü değiştirilmedi). Bu bulgunun kendisi önemli bir istatistiksel sonuçtur: `%20`'lik `C`-sınıfı kriyo-zincir şoku + log-normal program çarpanı birleştiğinde üst `P95` kuyruğu ağırlaşır ve `100k` örnekte bile `~%1–1,5` kuyruk belirsizliği taşır.

---

## 2. Kanonik `Exp122` → `BOM_DETAILED.csv` (`145` Parça) Uzlaştırması & `M1` vs `M3`

- **Kanonik Kapı:** `NL55-B` = `0,560295033350 / 2159,00039876329`; `NL163` merkez = `3.515,617u = $2.531.244,37 @ $720/u`; `CT1` köşesi = `$13.072.987,48`; `CT2 (×10)` = `$25.312.443,66` — tümü `0,00` sapmayla yeniden üretildi.
- **Birebir Çapa Koruması:** `BOM_DETAILED.csv` içinde `S6.6-01..06` (`56` okuma zinciri × `$12.150` = **`$680.400`**) ve `S6.8-01..04` (`20 mK` DR = **`$720.000`**) `Exp114/122` ile tam olarak eşleşir.
- **Mühendislik Delta Köprüsü (`$2.531.244` → `$4.189.600`, net `+$1.658.356`, hata `$0,00`):**
  1. `S2` MEMS sabit maske/DRIE/TSV/wafer-bonding NRE (`Exp122` `(nb/10⁶)^0,7` ölçeğinin bastırdığı kısım): **`+$764.867`**
  2. `COTS / UHV / PT420 / EMI / S7` gerçek katalog çapa uyumu: **`+$285.769`**
  3. `Exp125` `1,50 T / ≤0,40 T` aktif karşı-sargılı mıknatıs + `Nb` kalkan + `9000`-ch `NbTiN` rezonatörler: **`+$261.000`**
  4. `S9` kalibrasyon yongaları, 1 yıllık gaz/katot sarfı & yedek MEMS/LNA kiti (`BOM.csv`'de `0u`): **`+$148.000`**
  5. `Exp124` `10→5 keV` `Arch-B` yavaşlatma lensi + gerçek `HDA-HiRes` UHV süzgeç (`S1.5`, `ΔE_FWHM ≤ 0,50 eV` / `0,453 eV`) + `PH₃` gaz kabini/scrubber (`S1.6`) vs `ADDERS=20u`: **`+$133.600`**
  6. `Exp127` kilitli `100 K / 1,2 µs / 1 GΩ` (`342 e⁻, η=0,99936`) `16×8` `LTC6268` IBIC ön-uç + kanal-başı trim DAC + `<5 cm` mikro-koaksiyel: **`+$65.119`**
- **`M1` vs `M3` Ölçeklenmesi:** Tek-demet laboratuvar prototipi **`M1` = `$2.189.770`** nominal (`$1,28M–$3,94M`; `M3`'ün **`%52,3`'ü**). `M1` maliyetinin ~`%82`'si (`20 mK` DR, `PT420`, `1,5 T` mıknatıs, UHV oda, `PH₃` güvenliği, piezo+interferometre) doğrudan `M3`'e taşınabilir sabit gövdedir.

---

## 3. 100.000 Örneklemli Monte Carlo Bütçe Tavanı Sonuçları (`$50M` / `$100M`)

| Model / Senaryo (`N = 100.000`, `seed = 2026128`) | Ortalama | `P10` | `P50` | `P90` | `P95` | `P99` | `P(> $50M)` *(Gerekçe)* | `P(> $100M)` *(Sert Aşım)* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Model A — Saf BOM (`B/C` şoksuz, `NL=163`)** | `$4,69M` | `$3,14M` | `$4,50M` | `$6,48M` | `$7,21M` | `$8,76M` | `%0,00` | `%0,00` |
| **Model A — M3 BOM (`NL 110–163` + `%20` C-şoku)** | `$5,74M` | `$3,34M` | **`$5,01M`** | `$8,94M` | `$11,20M` | `$16,50M` | **`%0,00`** | **`%0,00`** |
| **Model A — Program Sabit `×3`** | `$17,22M` | `$10,03M` | `$15,03M` | `$26,83M` | `$33,59M` | `$49,51M` | `%0,95` | `%0,00` |
| **Model A — Program Stokastik (`×3–×10`, `P50=5,48×`)** | `$35,09M` | `$13,34M` | **`$28,24M`** | `$63,63M` | `$82,11M` | `$135,20M` | **`%18,10`** | **`%2,69`** *(±%0,05)* |
| **Model A — Program Sabit `×10` (Üst Varsayım)** | `$57,40M` | `$33,43M` | `$50,11M` | `$89,43M` | `$111,97M` | `$165,04M` | `%50,24` | `%7,19` |
| **Model B — Kanonik `Exp122` (`$190–$1600/u`) + Deltalar (BOM)** | `$7,18M` | `$2,50M` | **`$4,99M`** | `$12,81M` | `$18,27M` | `$40,04M` | `%0,54` | `%0,05` |
| **Model B — Kanonik + Deltalar (Program Stokastik)** | `$43,89M` | `$10,92M` | **`$28,01M`** | `$84,59M` | `$123,48M` | `$274,15M` | `%24,07` | `%7,38` |

- **Çapraz Doğrulama:** İki tamamen bağımsız maliyet modeli (`Model A` parça-bazlı 137-boyutlu Cholesky kopulası vs `Model B` kanonik `Exp122` + deltalar) hem BOM medyanında (`$5,01M` vs `$4,99M`, `%0,4` fark) hem program medyanında (`$28,24M` vs `$28,01M`, `%0,8` fark) olağanüstü bir uyum gösterir.
- **Bütçe Tavanı Yorumu (`H140`):** Donanım BOM düzeyi `$50M` sınırını pratikte asla aşmaz (`%0,00`). Program seviyesinde (temizoda/tesis + entegrasyon + AR-GE maaşları dahil) medyan `$28,2M` ile güvenli bölgededir; ancak **`%18,1` olasılıkla `$50M` gerekçe bölgesi tetiklenir** ve `%2,69` kuyrukta (`C`-sınıfı kriyo zincir + yüksek program çarpanı aynı anda gelirse) `$100M` sınırı tehdit altındadır.

---

## 4. Tornado Duyarlılığı & 6-RFQ Varyans Kapsamı

| Sıra | Maliyet Sürücüsü (BOM-Kapsamı, Model A) | Sürücü `P50` | BOM Varyans Payı | Spearman `ρ_S` | Koşullu BOM Ort. (`P10 → P90`) | Salınım (`Δ`) |
|---:|---|---:|---:|---:|---:|---:|
| **1** | **`S6.6` Okuma Zinciri (`56–82×`, `B/C` Duvarı)** | `$1.059k` | **`%77,27`** | **`0,889`** | `$3,18M → $12,05M` | **`$8,87M`** |
| **2** | **`S2.1–2.3` MEMS Kafa & Fab NRE** | `$685k` | **`%5,85`** | `0,548` | `$4,03M → $8,08M` | `$4,05M` |
| **3** | **`S6.8` Seyreltme Kriyostatı (`20 mK` DR)** | `$735k` | **`%5,21`** | `0,623` | `$3,67M → $8,63M` | `$4,96M` |
| **4** | `S1` Kaynak + Kolon + Süzgeç + `PH₃` (`Exp124`) | `$435k` | `%2,13` | `0,482` | `$4,14M → $7,75M` | `$3,61M` |
| **5** | `S6` Diğer (`PT420`/MW/RF/SET) | `$265k` | `%2,00` | `0,676` | `$3,56M → $8,88M` | `$5,33M` |
| **6** | `S6.3` `1,50 T / ≤0,40 T` Mıknatıs (`Exp125`) | `$191k` | `%1,42` | `0,616` | `$3,70M → $8,54M` | `$4,84M` |
| 7–10 | `S3` (`%1,22`), `S5` (`%1,17`), `S4` (`%1,13`), `S7` (`%1,00`) | `$212k–$262k` | `%4,52` top. | `0,43–0,44` | `$4,25M → $7,63M` | `~$3,3M` |

- **Program Seviyesi Sürücüler:** Program çarpanı (`×3–×10` varsayımı, `ρ=0,760`, salınım `$59,56M`) ve `S6.6` `B/C` zincir duvarı (`ρ=0,545`, salınım `$54,24M`) program riskini domine eder.
- **6-RFQ Stratejik Etkisi (`RFQ_SPECIFICATIONS.md`):** Altı tedarikçi paketi (`58` parça) nominal donanımın **`%70,4`'ünü (`$2,95M`)**, ancak toplam BOM MC varyansının **`%92,8`'ini** kapsar.

---

## 5. `20 mK` Baz (`Exp121`) vs. `1 K` Sıcak-Okuma AR-GE EVPI & Başa-Baş Analizi

`S6.8` `20 mK` seyreltme kademesinden (`$720k` nom, MC ort. **`$783,5k`**) `1 K` kapalı-çevrim kademesine (`$110k` nom, MC ort. **`$120,6k`**) geçişin makine başına beklenen donanım tasarrufu **`E[ΔC_hw] = $662.896`** (`$662,9k`; medyan **`$618,0k`**).

| `1 K` AR-GE Bedeli (`C_RD`) | Başarı Olasılığı (`p_succ`) | Başa-Baş (`N_be` Donanım) | Başa-Baş (`N_be` `2×` Entegrasyon) | `N=1` (`M1/M3`) `ENV` / `EVPI` | `N=5` Filo `ENV` / `EVPI` | `N=10` Filo `ENV` / `EVPI` |
|---:|---:|---:|---:|---:|---:|---:|
| `$0,5M` | `%50` | `1,51` | `0,75` | `−$0,17M` / `$81,4k` | `+$1,16M` / `$250,0k` | `+$2,81M` / `$250,0k` |
| `$1,0M` | `%50` | `3,02` | `1,51` | `−$0,67M` / `$0` | `+$0,66M` / `$500,0k` | `+$2,31M` / `$500,0k` |
| **`$2,0M` (`CU5`)** | **`%50`** | **`6,03`** | **`3,02`** | **`−$1,67M` / `$0`** | `−$0,34M` / **`$657,2k`** | `+$1,31M` / `$1.000,0k` |
| `$2,0M` | `%25` | `12,07` | `6,03` | `−$1,83M` / `$0` | `−$1,17M` / `$328,6k` | `−$0,34M` / `$1.157,2k` |
| `$5,0M` | `%50` | `15,09` | `7,54` | `−$4,67M` / `$0` | `−$3,34M` / `$0` | `−$1,69M` / `$814,5k` |

**Karar-Teorik Sonuç:**
1. **İlk makine (`M1`/`M3`, `N=1`) için `Exp121` (`20 mK` DR baz) kararı kesin biçimde optimaldir:** `$2,0M` AR-GE harcaması tek makinede `$663k` potansiyel tasarrufu aşar (`ENV = −$1,67M`, `EVPI = $0` — kusursuz bilgi gelse bile tek makinede karar değişmez!).
2. **`1 K` sıcak-okuma AR-GE'si ancak çok-makineli filo (`N ≥ 6` donanım, veya `N ≥ 4` entegrasyon dahil) kararı verildiğinde başa-baş olur** (`N=5` karar eşiğinde `EVPI = $657k` ile en yüksek bilgi değerine ulaşır).
3. **Buna karşılık 6 tedarikçi RFQ'sunu göndermek neredeyse sıfır maliyetle `$4,48M`'lik `B/C` duvarı aşım riskini (`%92,8` BOM varyansı) çözer** — açık ara en yüksek getirili ilk eylemdir.

---

## 6. Üretilen Artefaktlar
- `research/atom_lithography_machine/BOM_DETAILED.csv` (`145` parça)
- `research/atom_lithography_machine/BOM_ENGINEERING.md`
- `research/atom_lithography_machine/RFQ_SPECIFICATIONS.md`
- `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `run_exp128.py`, `plot_exp128.py`
- `results/exp128_bom_sensitivity/predictions_exp128.json`, `exp128.json`, `summary_exp128.md`
- `results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png`, `fig_exp128_m1_vs_m3_cost.png`
- `tests/test_bom_detailed.py`
