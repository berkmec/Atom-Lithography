# Exp138 (`H156`) — Kusurlu / Eksik Hücreli Döndürülmüş Yüzey Kodu Hata-Tolerans Eşiği, Tam Blossom MWPM Kod Çözücü ve `v5.0` Makine Ölçeklemesi

- **Deney / Hipotez:** `exp138_defective_surface_code_ft` (`H156`)
- **Tarih:** `2026-11-23`
- **Epistemik Etiket:** `{Sayısal-Simülasyon}` / `{Model}` (`no_lab_measurement = true`)
- **Ön-Kayıtlı Yargı Özeti:** **`6/7 PASS` (`1/7` dürüst `FAIL`: `FT5`)** — `success_rule_met = true` (kural: `>= 5/7 PASS` + sıfır cebir/komütasyon/taşınabilirlik hatası; ön-kayıtlı `predictions_exp138.json` eşikleri sonuç sonrası **kesinlikle değiştirilmemiştir**).
- **Denetim Kilidi (`Yazar != Denetçi`):** Bu rapor yazar (`Hydrogen` / `physics-early`) çıktısıdır; bağımsız `KABUL` onayı yalnızca sıfır bağlamlı `Carbon` denetçisi tarafından verilebilir.

---

## 1. Yönetici Özeti ve `v5.0` Ana Bulguları `{Sayısal-Simülasyon}`

`Exp138`, Atom Litografi Makinesi `v5.0` yığınının altı üst-akış fiziksel çıpasını (`Exp136` `²⁹Si` verimi ve `XY8-N64` `T₂e`, `Exp137` tam 16-Pauli `M4` veri yolu `CZ` kanalları, `Exp139` Rota C yük-gürültü pasivasyonu `S_ε = 0.3897 µeV/√Hz` ve flip-flop verimi `0.9770`, `Exp140` `N_mux* = 32` okuma hatası `p_meas = 0.003861` ve `2,887` hücrelik `20 mK MXC` termal tavanı, `Exp132` BOED `FNR = 0.201%`, `Exp126` tek-kübit `p_1q = 0.00083`) tek bir **devre-seviyesi 3B Dedektör Hata Modeli (`DEM`) + tam Edmonds Blossom `MWPM` (`networkx.min_weight_matching`) + eksik-hücre süper-stabilizatör ayar-deformasyonu** simülatöründe birleştirir.

1. **Devre-Seviyesi Hata-Tolerans Eşiği (`p_2q,th`) ve `v4.0 -> v5.0` Kırılımı:**
   - Kanca-hatası korumalı (`hook-immune`) Tomita-Svore `4`-adımlı `CZ/CNOT` çizelgesi (`X`-plaketleri N-sırası, `Z`-plaketleri Z-sırası) ile `d = 3, 5, 7, 9, 11` (`2d² - 1 = 17, 49, 97, 161, 241` aktif kübit) için **`H_X H_Z^T ≡ 0 (mod 2)`**, `d_circ = d` ve **`0` graf-dışı hiper-kenar** doğrulanmıştır.
   - `Exp137` `P4` tam 15-terimli `pauli_16` profili + `Exp140` `p_meas = 0.003861` + `Exp126` `p_1q = 0.00083` + tam `4`-`CZ` + okuma (`8.93 µs`) döngüsü üzerinde `Exp136` `p_idle,Z = 0.000316` altında birleşik `(X+Z)` **döngü-başı (`per-round`) devre-seviyesi eşiği** **`p_2q,th = 1.60% ± 0.17%`** (`F_avg,th ≈ 98.72%`; `Z`-bellek `1.62%`, `X`-bellek `1.75%`; `d`-döngü blok kesişimi `1.01%`) olarak ölçülmüştür.
   - **Dürüst Negatif Kontroller (`FT2 PASS`):** `v4.0` Çıplak `P1` (**Senaryo A**, `p_2q = 39.25%`, `Λ = 0.00`), pasive edilmemiş `P4` `S_ε = 1.0` 6-çift (**Senaryo B1**, `p_2q = 6.65%`, `Λ = 0.62`) ve pasive edilmemiş `P4` hızlı çiftler (**Senaryo B2**, `p_2q = 2.79%`, `Λ = 0.74`) **kesin olarak eşiğin üzerindedir** — hem `P4` yankısı hem de `Exp139` Rota C yük-gürültüsü pasivasyonu olmadan hata-tolerans **imkansızdır**.
2. **Rota C Eşik Geçişi ve `Q_r` / `p_2q` Ölçekleme Gerçeği (`FT3 PASS`):**
   - `Q_r = 2×10⁵` baz rezonatörde `Exp139` nominal Rota C (`S_ε = 0.390`, **Senaryo C2**, `p_2q = 1.41%`) eşiği yalnızca kıl payı aşar (**`Λ = 1.04`**); `S_ε = 0.25` (**Senaryo C3**, `p_2q = 1.24%`) **`Λ = 1.13`** verir (pratik `d*` patlar).
   - `NbTiN` veri yolu rezonatörünü **`Q_r = 5×10⁵`** düzeyine çıkarmak nominal Rota C'de (**Senaryo D1**, `p_2q = 1.08%`) **`Λ = 1.26`**, en iyi Rota C bandında (**Senaryo D2**, `S_ε = 0.25`, `p_2q = 0.92%`, `F_avg = 99.26%`) **`Λ = 1.40` (95% CI `[1.31, 1.50]`)** sağlar (`ε_L,round(d=3) = 8.72×10⁻³ -> ε_L,round(d=11) = 2.44×10⁻³`; `+p_leak` LRU cezası altında `Λ = 1.39`, `Exp140` `3 µs` optimal okumada `Λ = 1.38`).
   - **Kritik Mühendislik Bulgusu (`Exp141` Köprüsü):** Senaryo D2 (`Λ = 1.40`) hata-tolerans eşiğini kanıtlamaya yeterlidir, ancak `ε_L = 10⁻⁹` için `d* = 99` (`19,601` aktif hücre/mantıksal, `100` mantıksal kübit için `679` `LD400/PT420` kriyostat) gerektirir. İki-kübit hatasını yalnızca **`1.84×`** daha aşağı çekmek (**Senaryo D3 Hedef**, `p_2q = 0.50%`, `F_avg = 99.60%`) bastırma çarpanını **`Λ = 2.52`** düzeyine sıçratır, `ε_L = 10⁻⁹` ayak izini **`7.2×` küçültür** (`d* = 37`, `2,737` aktif hücre = tek `LD400/PT420` kriyostatın `2,887` MXC sınırına sığan tam bölünmemiş 1 mantıksal kübit!) ve `100` mantıksal kübit filosunu **`679 -> 100` kriyostata** düşürür.
3. **Eksik-Hücre Süper-Stabilizatör Bozulması ve Dürüst `FT5 FAIL` Bulgusu:**
   - Rastgele ölü veri + ölü ansilla kümelerinin **%100'ünde** (`100%` gerçekleşme) süper-stabilizatör komütasyonu `H_X_def H_Z_def^T ≡ 0 (mod 2)` tam korunmuştur.
   - Ancak `d = 7` (`97` fiziksel hücre = `49` veri + `48` ansilla) üzerinde ölü ansillaların Auger et al. (2017) çap-2 ağırlık-8 süper-stabilizatör delikleri oluşturması nedeniyle **`f = 1.0%, N_cand = 6` (`p_drop = 1.31%`) etkin mesafeyi yalnızca `d_eff / d = 79.0%` (`5.53/7`) düzeyinde tutabilmiş** (`f* = 1.5% + 2 MV/m, N_cand = 3` ise `81.1%`), bu yüzden ön-kayıtlı `>= 85%` kriteri **dürüstçe `FAIL` (`FT5`)** vermiştir.
   - `>= 85%` mesafe korunması için ya **`f = 1.0%, N_cand = 8`** (`p_drop = 0.310% -> d_eff/d = 94.6%`) ya da `Exp136` **`f* = 1.5% + 2 MV/m` Stark + `N_cand = 6`** (`p_drop = 0.021% -> d_eff/d = 99.5%`, `d_eff = 6.96/7`, neredeyse kusursuz!) gereklidir.
   - `Exp132` BOED spektroskopi yanlış-negatif oranı (`FNR = 0.201%`), `N_cand = 6` noktasında `p_drop` değerini yalnızca **`+0.017` yüzde puan (`f=1.0%`)** ve **`+0.0008` yüzde puan (`f*=1.5%`)** kaydırmaktadır (**ihmal edilebilir**).

---

## 2. Üst-Akış `v5.0` Fiziksel Çıpaları `{Model}`

Tüm girdi parametreleri çalışma zamanında diskteki salt-okunur üst-akış JSON dosyalarından dinamik olarak okunmuştur:

| Kaynak | Parametre | Değer | Rolü |
| :--- | :--- | :--- | :--- |
| `Exp136` (`f=1.0%`) | `P_yield`, `T₂e (XY8-N64, α=2)` | `0.5275`, `20.306 ms` | Baz izotop slot verimi ve boşta faz-bozulma (`p_idle,Z = 2.20×10⁻⁴`) |
| `Exp136` (`f*=1.5%+2MV/m`) | `P_yield (Stark)`, `T₂e (XY8-N64)` | `0.7750`, `14.135 ms` | Yükseltilmiş izotop+Stark verimi ve `p_idle,Z = 3.16×10⁻⁴` |
| `Exp139` (`Rota C`) | `S_ε` (nominal / bant), `p_ff (C>=100)` | `0.3897 µeV/√Hz` (`[0.283, 0.549]`), `0.9770` | Yük-gürültü köprüsü ve flip-flop elektrot verimi |
| `Exp137` (`P4`, `part3+4`) | Tam `pauli_16`, `t_gate`, `(Q_r, S_ε)` haritası | `p_2q = 0.0092–0.3925`, `t_gate = 1.683 µs` | 15-terimli ilişkili 2-kübit `CZ` gürültü kanalı ve `p_leak` |
| `Exp140` (`N_mux*=32`) | `p_meas (2 µs / 3 µs)`, MXC tavanı | `0.003861` / `0.002232`, `2,887` hücre (`1,024` nom.) | Sendrom okuma hatası ve tek `LD400/PT420` kriyostat tavanı |
| `Exp132` (`BOED 20 mK`) | `FNR`, `FPR` | `0.002008`, `0.000000` | Kusurlu/eksik hücre maskesine spektroskopi yanlış-negatif katkısı |
| `Exp126` (`Rx_pi2 32D`) | Ortalama 1Q kapı hatası `p_1q` | `0.000830` (`F_1q = 0.99917`) | Veri/ansilla tek-kübit ve DD darbe hata zemini |
| Türetilmiş 4-`CZ` Döngüsü | `T_cycle = 4·t_gate + τ_ro + 0.2 µs` | `8.932 µs` (`Exp140` 1-`CZ` demosu `2.620 µs`) | Muhafazakar tam 4-adımlı yüzey kodu sendrom döngü süresi |

---

## 3. Ön-Kayıtlı `FT1–FT7` Doğrulama Tablosu `{Sayısal-Simülasyon}`

| Kimlik | Ön-Kayıtlı Hipotez Özeti | Ölçülen Sonuç | Yargı |
| :--- | :--- | :--- | :--- |
| `FT1` | `d=3..11` tam CSS cebiri (`2d²-1`, `d_circ=d`, `0` graf-dışı) ve `p_2q,th ∈ [0.70%, 2.00%]` | `all_algebra_exact = True`; `p_2q,th = 1.60% ± 0.17%` (`d`-blok: `1.01%`) | **PASS** |
| `FT2` | Negatif kontroller: Senaryo A (`39.25%`), B1 (`6.65%`), B2 (`2.79%`) eşik üstü (`Λ < 1`, `ε_blk(7) > ε_blk(3)`) | A: `Λ=0.00` (`0.749->0.763`); B1: `Λ=0.62` (`0.493->0.749`); B2: `Λ=0.74` (`0.197->0.552`) | **PASS** |
| `FT3` | Senaryo D2 (`Q=5e5, S=0.25`) eşik altı (`Λ > 1.15`, `ε_rnd(11) < ε_rnd(3)`) ve D3 (`0.50%`) `Λ >= 2.0` | D2: `Λ = 1.40` (`0.00872 -> 0.00244`); D3: `Λ = 2.52` (`0.00351 -> 0.00011`) | **PASS** |
| `FT4` | Tam `pauli_16` ile `Z`- ve `X`-bellek tutarlılığı (`ε_tot >= max(ε_X, ε_Z)`, `p_th(Z) >= 0.90·p_th(X)`) | `combined_bound = True`; `p_th(Z) = 1.62% >= 0.90 × 1.75% = 1.57%` (`Z/X = 0.924`) | **PASS** |
| `FT5` | Süper-stabilizatör komütasyonu (`100%`), `d_eff/d >= 85%` (`f=1%, N=6` ve `f*=1.5%, N=3`), BOED `Δp_drop < 0.05%` | Komütasyon `100%`, `f1 N1=0.02`, `f15 N6=99.5%`, BOED `+0.017%` PASS; ancak **`f1 N6 = 79.0%`** ve **`f15 N3 = 81.1%` < `85%`** | **FAIL** |
| `FT6` | `ε_L = A·Λ^{-(d+1)/2}` ile `10⁻⁶/10⁻⁹/10⁻¹²` `d*`, `N_active`, `N_phys`, `100L` kriyostat sayısı ve `Exp141` arayüzü | `target_logical_error_rates` tam, monoton ve `wafer_econ141.py` ile canlı testli | **PASS** |
| `FT7` | `>= 2,000` atış/nokta + Wilson %95 GA, `0` sabitlenmiş yol, `2400×1400` PNG, `0` GFM hatası, `>= 8` pytest | `min_shots = 2,000`, `0` hardcoded path, `2400×1400` CRC-temiz PNG, `10/10` pytest | **PASS** |

---

## 4. Senaryo Karşılaştırması: `v4.0` -> `v5.0` Rota C -> Derin FT (`d = 3..11`) `{Sayısal-Simülasyon}`

Her noktada `Z`-bellek ve `X`-bellek bağımsız olarak `2,000–4,000` Monte Carlo atışı ve tam Edmonds Blossom MWPM ile çözülmüş, birleşik mantıksal hata `ε_L,tot = 1 - (1 - ε_Z)(1 - ε_X)` ve Google Quantum AI tam bellek-bozulma ters çevrimi `ε_r = 0.5·(1 - max(0, 1 - 2·ε_blk)^{1/d})` ile döngü-başı hata `ε_L,round` hesaplanmıştır:

| Senaryo | `p_2q` (`F_avg`) | `ε_L,round (d=3)` | `ε_L,round (d=7)` | `ε_L,round (d=11)` | `Λ_round` (95% GA) | `Λ_block` | Rejim |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `A`: `v4.0` Çıplak `P1` (`S=1.0, Q=2e5`) | `39.25%` (`68.60%`) | `0.70725` | `0.75000` | — | `0.00` (doymuş) | `0.00` | Eşik Üstü (Çökük) |
| `B1`: Pasivesiz `P4` 6-çift (`S=1.0, Q=2e5`) | `6.65%` (`94.68%`) | `0.23329` | `0.60326` | — | `0.62` (`[0.62, 0.62]`) | `0.84` | Eşik Üstü |
| `B2`: Pasivesiz `P4` hızlı (`S=1.0, Q=2e5`) | `2.79%` (`97.77%`) | `0.07340` | `0.13794` | — | `0.74` (`[0.69, 0.79]`) | `0.63` | Eşik Üstü |
| `C1`: Rota C `P4` 6-çift (`S=0.50, Q=2e5`) | `2.31%` (`98.16%`) | `0.05059` | `0.08475` | — | `0.77` (`[0.77, 0.77]`) | `0.60` | Eşik Üstü |
| `C2`: Rota C Nom. hızlı (`S=0.39, Q=2e5`) | `1.41%` (`98.88%`) | `0.02169` | `0.02004` | `0.01910` | `1.04` (`[1.02, 1.06]`) | `0.79` | Eşik Sınırı |
| `C3`: Rota C En İyi hızlı (`S=0.25, Q=2e5`) | `1.24%` (`99.01%`) | `0.01597` | `0.01257` | `0.00986` | `1.13` (`[1.10, 1.15]`) | `0.84` | Zayıf FT |
| `D1`: Rota C Nom. Yüksek-Q (`S=0.39, Q=5e5`) | `1.08%` (`99.13%`) | `0.01427` | `0.00843` | `0.00555` | `1.26` (`[1.19, 1.34]`) | `0.93` | Eşik Altı FT |
| **`D2`: Rota C Yüksek-Q (`S=0.25, Q=5e5`)** | **`0.92%` (`99.26%`)** | **`0.00872`** | **`0.00463`** | **`0.00244`** | **`1.40` (`[1.31, 1.50]`)** | **`1.03`** | **Eşik Altı FT (`v5.0`)** |
| `D2 + LRU` sızıntı cezası (`+p_leak=0.038%`) | `0.92% + 0.04%` | `0.01132` | `0.00532` | `0.00464` (`d=9`) | `1.39` (`[1.28, 1.51]`) | `0.95` | Duyarlılık (`-1%`) |
| `D2 + 3 µs RO` (`Exp140` `p_meas=0.223%`) | `0.92%` (`99.26%`) | `0.00816` | `0.00361` | `0.00355` (`d=9`) | `1.38` (`[1.16, 1.64]`) | `0.97` | Duyarlılık (tutarlı) |
| **`D3`: Hedef Derin-FT (`Q>=1e6, S<=0.15`)** | **`0.50%` (`99.60%`)** | **`0.00351`** | **`0.00050`** | **`0.00011`** | **`2.52` (`[2.02, 3.15]`)** | **`1.86`** | **Derin FT Hedefi** |

---

## 5. Eksik-Hücre Süper-Stabilizatör Bozulması ve `Exp132` BOED `FNR` Denetimi `{Sayısal-Simülasyon}`

Her `(rejim, N_cand, d)` noktası için `200` rastgele kusurlu kafes üretilmiş (`100%` tam komütasyon `H_X_def H_Z_def^T = 0`), ilk `25` kafes üzerinde `25 × 120 = 3,000` devre-seviyesi Blossom MWPM atışı çalıştırılmıştır:

| Rejim (`p_slot`) | `N_cand` | `p_drop` | `d_eff (d=5)` | `d_eff (d=7)` (`d_eff/d`) | `d_eff (d=9)` | Yama Sağkalım (`d=7`) | Kusurlu `ε_L,round` (`D2`, `d=7`) | Kusurlu `ε_L,round` (`D3`, `d=7`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `f=1.0%` (`0.5143`) | `1` | `48.57%` | `0.06` (`1.1%`) | `0.02` (`0.3%`) | `0.03` (`0.3%`) | `2.0%` | `0.75000` (çökük) | — |
| `f=1.0%` (`0.5143`) | `3` | `11.46%` | `1.67` (`33.4%`) | `2.09` (`29.9%`) | `2.57` (`28.6%`) | `95.0%` | `0.05390` | `0.03190` |
| `f=1.0%` (`0.5143`) | `6` | `1.312%` | `4.24` (`84.7%`) | `5.53` (`79.0%`) | `7.03` (`78.1%`) | `100.0%` | `0.01395` | `0.00230` |
| `f=1.0%` (`0.5143`) | `8` | `0.310%` | `4.78` (`95.6%`) | `6.62` (`94.6%`) | `8.37` (`93.0%`) | `100.0%` | `0.01024` | — |
| `f*=1.5%+2MV/m` (`0.7557`) | `1` | `24.43%` | `0.59` (`11.8%`) | `0.57` (`8.1%`) | `0.59` (`6.6%`) | `47.0%` | `0.14770` | — |
| `f*=1.5%+2MV/m` (`0.7557`) | `3` | `1.459%` | `4.20` (`83.9%`) | `5.67` (`81.1%`) | `6.84` (`76.0%`) | `100.0%` | `0.01298` | `0.00293` |
| **`f*=1.5%+2MV/m` (`0.7557`)** | **`6`** | **`0.021%`** | **`4.99` (`99.7%`)** | **`6.96` (`99.5%`)** | **`8.96` (`99.6%`)** | **`100.0%`** | **`0.00963`** | **`0.00129`** |
| `f*=1.5%+2MV/m` (`0.7557`) | `8` | `0.001%` | `5.00` (`100.0%`) | `6.99` (`99.9%`) | `8.99` (`99.9%`) | `100.0%` | `0.00798` | — |

- **`FT5 FAIL` Fiziksel Açıklaması:** `p_drop = 1.31%` (`f=1.0%, N_cand=6`) seviyesinde `97` hücreli `d=7` yamasında beklenen eksik hücre sayısı `1.27`'dir; bunların yarısı veri kübiti (`Δd ≈ -1`), yarısı ise Auger et al. (2017) ağırlık-8 süper-stabilizatör deliği açan ansilla (`Δd ≈ -1.5..2`) olduğundan `d_eff/d = 79.0%` olarak ölçülmüştür. Buna karşın `Exp136` `f*=1.5% + 2 MV/m` Stark + `N_cand = 6` kombinasyonu `p_drop = 0.021%` ile **`d_eff/d = 99.5%`** (neredeyse kusursuz) sağlar.
- **`Exp132` BOED `FNR = 0.201%` Denetimi:** İdeal `FNR = 0` ile karşılaştırıldığında `N_cand = 6` noktasında `Δp_drop = +0.000167` (`f = 1.0%`) ve `+0.000008` (`f* = 1.5%`), `Δd_eff = -0.05` (`f = 1.0%`) ve `-0.005` (`f* = 1.5%`) olup **tamamen ihmal edilebilir** düzeydedir.

---

## 6. `Exp141` (`$/logical qubit`) Makine Ölçekleme Arabirimi ve Modüler Kriyostat Bütçesi `{Model}`

`results/exp138_defective_surface_code_ft/exp138.json` dosyası üst-düzey `target_logical_error_rates` anahtarıyla `experiments/exp141_v5_digital_twin/wafer_econ141.py` (`evaluate_logical_qubit_economics`) fonksiyonuna doğrudan tak-çalıştır uyumludur (birincil `v5.0` referans noktası: `D2_v5_RotaC_P4_S0p25_fast_Q5e5`, `f*=1.5%+2MV/m, N_cand=6`, `Λ = 1.40`; ayrıca `part4_machine_scaling_scenarios` altında `C2, C3, D1, D2, D3` ve `N_cand=3/6` seçeneklerinin tamamı sunulur):

| Çalışma Noktası (`N_cand`, `d_eff/d`) | Hedef `ε_L` | `d*` (`d*_blk`) | `N_active = 2d*²-1` | `N_phys / L` | Mantıksal / Kriyostat (`2,887` MXC) | `100L` Kriyostat (`2,887` MXC) | `100L` Aktif Hücre |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `D2: Q=5e5, S=0.25` (`N=6`, `99.5%`) **[Exp141]** | `10⁻⁶` | `59` (`85`) | `6,961` | `41,766` | `0` (bölünmüş yama) | `242` | `696,100` |
| **`D2: Q=5e5, S=0.25` (`N=6`, `99.5%`) [Exp141]** | **`10⁻⁹`** | **`99` (`129`)** | **`19,601`** | **`117,606`** | **`0` (bölünmüş yama)** | **`679`** | **`1,960,100`** |
| `D2: Q=5e5, S=0.25` (`N=6`, `99.5%`) **[Exp141]** | `10⁻¹²` | `141` (`173`) | `39,761` | `238,566` | `0` (bölünmüş yama) | `1,378` | `3,976,100` |
| `D2: Q=5e5, S=0.25` (`N=3`, `81.1%`) | `10⁻⁹` | `123` (`159`) | `30,257` | `90,771` | `0` (bölünmüş yama) | `1,049` | `3,025,700` |
| `D1: Q=5e5, S=0.39` (`N=6`, `99.5%`) | `10⁻⁹` | `147` (`193`) | `43,217` | `259,302` | `0` (bölünmüş yama) | `1,497` | `4,321,700` |
| `D3: Hedef Derin-FT p=0.50%` (`N=6`, `99.5%`) | `10⁻⁶` | `21` (`29`) | `881` | `5,286` | `3` (nom. `1,024`: `1`) | `34` | `88,100` |
| **`D3: Hedef Derin-FT p=0.50%` (`N=6`, `99.5%`)** | **`10⁻⁹`** | **`37` (`45`)** | **`2,737`** | **`16,422`** | **`1` (tek kriyostat!)** | **`100`** | **`273,700`** |
| `D3: Hedef Derin-FT p=0.50%` (`N=6`, `99.5%`) | `10⁻¹²` | `51` (`61`) | `5,201` | `31,206` | `0` (bölünmüş yama) | `181` | `520,100` |

---

## 7. Yapılmayanlar / Kapsam Dışı ve Sınır Koşulları

- **Gerçek Laboratuvar Ölçümü Yok (`no_lab_measurement = true`):** Tüm hata oranları, eşikler ve ölçekleme projeksiyonları `Exp126–Exp140` sayısal-fizik modellerinden türetilmiş devre-seviyesi Monte Carlo simülasyonlarıdır; gerçek `²⁸Si/³¹P` `M4` donanım ölçümü değildir.
- **Korelasyonlu / Uzay-Zamansal Çok-Kübit Sızıntı & Kozmik Işınlar:** Sızıntı (`p_leak`) standart Pauli-twirled LRU depolarizasyon duyarlılığı (`D2 + LRU`) ile üst-sınırlanmıştır; uzun ömürlü çok-döngülü sızıntı birikimi veya kozmik ışın patlamaları (burst errors) modellenmemiştir.
- **Kriyostatlar-Arası Bağlantı Kaybı:** `N_active > 2,887` durumlarında (`D2` `d* = 59, 99, 141`) mantıksal yamanın birden fazla `LD400/PT420` kriyostat arasında bölünmesi gerekir; kriyostatlar-arası mikrodalga/optik dikiş (`seam`) kapı hatası ayrı modellenmemiş, bu yüzden tek kriyostata sığan `D3` (`p_2q = 0.50%`, `d* = 37`, `2,737 <= 2,887`) hedefi açık mimari eşik olarak vurgulanmıştır.
- **Kod Ailesi:** Standart CSS döndürülmüş yüzey kodu kullanılmıştır; `Exp137` `Z`-sapması (`η_Z ≈ 1.5–1.7`) hafif olduğundan `XZZX` dönüşümü `~5–10%` ek marj verebilir ancak `D2 -> D3` kapı iyileştirme ihtiyacını ortadan kaldırmaz.

---

## 8. Üretilen Artefaktlar

- `experiments/exp138_defective_surface_code_ft/rotated_surface_code138.py` — Döndürülmüş yüzey kodu cebiri, süper-stabilizatör ayar-deformasyonu, 3B `Pauli-16` DEM derleyicisi ve tam Edmonds Blossom `MWPM` kod çözücüsü.
- `experiments/exp138_defective_surface_code_ft/run_exp138.py` — 8-çekirdekli paralel Monte Carlo simülasyon ve `Exp141` ölçekleme boru hattı.
- `experiments/exp138_defective_surface_code_ft/fig_exp138.py` — `2400 × 1400` 4-panelli PyCairo şekil üreteci.
- `results/exp138_defective_surface_code_ft/predictions_exp138.json` — Deney öncesi mühürlenmiş `FT1–FT7` tahminleri.
- `results/exp138_defective_surface_code_ft/exp138.json` — Ham Monte Carlo sayımları, eşik kesişimleri, kusurlu kafes istatistikleri ve `Exp141`-uyumlu `target_logical_error_rates`.
- `results/exp138_defective_surface_code_ft/fig_exp138_surface_code_ft.png` — `2400 × 1400` 4-panelli görsel.
- `tests/test_exp138.py` — `10` yazılım regresyon testi (cebir, süper-stabilizatör, MWPM, `Exp141` entegrasyonu, PNG CRC, GFM linter, sıfır sabitlenmiş yol).
