# Exp126 — Tam 32-Boyutlu Kuantum Hamiltonyen GRAPE, İç-İçe XY8/CPMG Dinamik Ayrıştırma & 16-Hücreli Atom Programlanabilirliği

**Tarih:** 2026-11-23 | **Donanım:** NVIDIA GeForce RTX 2060 SUPER (PyTorch `2.14.0+cu130`, `complex128` tam üniter matris üsteli) | **Çalışma Süresi:** `2397,5 s`  
**Epistemik Durum:** `no_lab_measurement=true` (`{Model}` / `{Sayısal-Simülasyon}` — fiziksel laboratuvar ölçümü, yonga üretimi veya deneysel atom manipülasyonu yapılmamıştır).  
**Ön-Kayıtlı Tahminler:** `results/exp126_atom_cell_programming/predictions_exp126.json` (hesaplamadan önce yazıldı, sonradan değiştirilmedi) → **`5/8 PASS`, `3/8 FAIL` (`success_rule_met=false`)**.

---

## 1. Yönetici Özeti & Temel Fiziksel Bulgular

`Exp126`, Atom Litografi Makinesi'nin açık **Risk `R3`** ("elektron π darbeleri aşırı-ince yarılmayı da yeniden odaklar; gerçek dizide DD, çekirdek koşullu kapılarıyla iç-içe tasarlanmalıdır", `summary_exp63.md`) maddesini `Exp63`'ün analitik `(1-ε)^N exp(-T/T2(N))` kestiriminden çıkarıp **tam `2⁵ = 32`-boyutlu (`1` adet `³¹P` elektronu + `4` adet aktif `²⁹Si` çekirdeği + tüm seküler dipol-dipol `J_ij` + tüm `448` banyo seyirci çekirdeği)** Hamiltonyen simülasyonuna taşır ve kullanıcının **"atomu/hücreyi programlayabilmek"** hedefini 16 heterojen sertifikalı silisyum hücresinde 5 mantıksal kuantum programıyla nicel olarak sınar.

**Dört ana fiziksel keşif ve kapanış sonucu:**

1. **Risk `R3` Tam 32B Hamiltonyen Düzeyinde Kapandı (`P126_4 PASS`):**
   - Varsayılan ürün çalışma noktasında (`Exp62 F1`, `f=%1`, `T2e=1,269 ms`, `N_total=64` iç-içe `XY8` elektron π darbesi, `ε=10⁻³`, tüm `448` banyo seyircisi ve `J_ij` dahil):
     - **`α=1` (`1/f` banyo): `Q_32D = 0,9209`** (`≥ 0,85` PASS; `Exp63` muhafazakâr `β=1` kestirimi `0,8851`'in `+3,58` puan üstünde).
     - **`α=2` (`1/f²` OU spektral difüzyon): `Q_32D = 0,9433`** (`≥ 0,85` PASS; `Exp63` `0,9250`'nin `+1,83` puan üstünde).
   - **Yeni fiziksel tatlı nokta ve DDRF tavanı keşfi:** `F1` üzerinde tam `N_total ∈ {0, 8, 16, 32, 64, 128}` taraması, gerçek global optimumun **`N_total = 32` (`N_dd = 8` / kapı: `α=2 → 0,9648`, `α=1 → 0,9260`, 448-seyirci örtüşmesi `0,9889`)** olduğunu; buna karşılık `Exp63`'te analitik olarak çalışan **`N_total = 128` (`N_dd = 32` / kapı, `f_mod = 32 kHz`)** noktasının gerçek Hamiltonyende **XY8 aşırı-ince odaklama / DDRF seyirci rezonansı** nedeniyle çöktüğünü (`ideal = 0,5437`, `sp_ovl448 = 0,0972`) ortaya çıkardı.
2. **İç-İçe `XY8` Altında DDRF Seyirci Çapraz Konuşması & RF Rabi Genlik Payı Keşfi (`F1 q3`, `min_gap = 6,89 kHz`):**
   - Taşıyıcısı `±A_k/2` arasında `XY8` ile anahtarlanan sıradan pürüzsüz bir `GAUSS500` darbesi, modülasyon frekansı `f_mod = N_dd/(2T)` en yakın seyirci boşluğunu (`6,89 kHz`) aştığında seyirci ayrımını sıfırlayarak tüm banyo örtüşmesini **`0,9992` (`N_dd=0`) → `0,2035` (`N_dd=8`) → `0,000537` (`N_dd=16`) → `1,51×10⁻⁶` (`N_dd=32`)** düzeyine çökertir.
   - `Exp61`'in eski `5 kHz` RF sınırı `N_dd=16` altında bu sıkıştırmayı yenemez (`F_nom = 0,7716`, `worst = 0,7034`). Gerçekçi Si:P NMR bobini genlik payında (**`10–15 kHz`**, `B₁ ≈ 1,2–1,8 mT`, Pla vd. *Nature* 2013 `~30 kHz` sınırının altında) iki-aşamalı GPU `XY8`-GRAPE sentezleyicisi 448 seyirci örtüşmesini **`0,000537 → 0,9919`** (`1846×` iyileştirme) ve 32B nominal sadakati **`0,9986`** düzeyine çıkarır.
3. **`XY8` vs `CPMG` Evrensel Eksen Koruması (`P126_5 PASS`):**
   - Sistematik π-darbe aşırı dönme hatasında (`δθ_sys = 2√(10⁻³) = 63,25 mrad`, `N=64`): **`XY8`** hem `GHZ_X` (`0,9767`) hem `GHZ_Y` (`0,9756`) eksenlerini kendi-telafisiyle korurken, **`CPMG`** iç-içe RF altında her iki eksende de koherent olarak çöker (`0,6454 / 0,6512`, `XY8` üstünlüğü **`+0,3245`**; `100 mrad`'da **`0,9555` vs `0,3366`, `+0,6189`**).
   - `ε = 10⁻²` darbe hatası tavanı doğrulandı (`Q_32D = 0,6382 < 0,80`).
4. **16 Heterojen Silisyum Atom Hücresinde Çok-Hücreli Programlanabilirlik (`P126_6`, `P126_7`, `P126_8` TAMAMI PASS):**
   - `f=%1` epitaksiyel banyodan bağımsız çekilen 16 tekil sertifikalı hücrenin (`16/16` benzersiz `{A_k}`, `CV = %55,6`, tümünde `Lie = 1023/1023`, `Vandermonde = 8/8 & 4/4`, `D0 17,5 s` maks sızıntı `≤ 7,76×10⁻⁹`) her birine özel derlenen `GRAPE + XY8` darbe çizelgeleriyle gerçekçi `f=%1, α=2, ε=10⁻³` gürültüsü altında 5 programın 16-hücre ortalaması:
     - **`Bell`:** `0,9501` (en kötü hücre `0,9416`) | **`GHZ-4`:** `0,9401` (en kötü `0,9263`) | **`Grover-2`:** `P(|11⟩) = 0,9237` (tam durum `0,8896`) | **`BitFlip-3` QEC:** **`0,8878`** (kodlanmamış `X`-hatası `0,0000` iken!) | **`QFT-3`:** `0,8377`.
   - `1 µm` hücre adımında hücreler arası dipol etkileşimi **`9,50×10⁻⁹ Hz`** (`< 10⁻⁶ Hz`) olup senkronize FDMA/yerel-AWG mimarisinde **`16×` paralel hızlanma** sağlar.

---

## 2. Ön-Kayıtlı Hükümler Tablosu (`predictions_exp126.json` → `exp126.json`)

| Kimlik | Ölçüt Özeti | Ölçülen Değer (32B CUDA) | Eşik | Hüküm |
|---|---|---|---|---|
| `P126_1` | `F1` 16 kapı birimlik / nominal / köşe / seyirci | `u_err=3,47e-12`, `nom_min=0,99423`, `wc_min=0,97264`, `sp_min=0,96194` | `<1e-11`, `≥0,995`, `≥0,985`, `≥0,998` | **FAIL** *(kıl payı + `q3` 6,89 kHz)* |
| `P126_2` | `F1` tüm 6 çift `CZ`/`CNOT` (ide + gürültülü) | `CZ_min=0,98279`, `CNOT_min=0,98730`, `leak_max=3,61e-3`, `CZ_noisy_mean=0,94442` | `≥0,985`, `<1e-3`, `≥0,85` | **FAIL** *(Çift `(2,3)` sızıntı/sadakat)* |
| `P126_3` | 32B Hahn-eko `1/ω^α` kalibrasyonu (`4×2`) | 7/8 hücre `≤0,0322`; `F1 α=2` `W=0,3087` (`err=0,0592`, `n_traj=512`) | `≤0,05` | **FAIL** *(1/8 MC örnekleme sapması)* |
| `P126_4` | **Risk `R3`**: `F1 N=64` 32B `GHZ-4` (`α=1 & 2`) | `α=1: 0,9209` (`Exp63: 0,8851`), `α=2: 0,9433` (`Exp63: 0,9250`) | her ikisi `≥0,85` | **PASS** |
| `P126_5` | `ε=10⁻²` tavanı & `XY8 − CPMG` (`δθ=63,2 mrad`) | `Q(ε=10⁻²)=0,6382`; `XY8−CPMG = +0,3245` (`0,9756` vs `0,6512`) | `<0,80`, `≥+0,20` | **PASS** |
| `P126_6` | 16 heterojen `f=%1` hücre sertifikasyonu | `16/16` tekil, `CV=0,556`, `Lie=1023`, `gap≥6,89 kHz`, `max J=6,65 Hz` | `16`, `1023`, `≥5 kHz`, `≤100 Hz`, `>0,20` | **PASS** |
| `P126_7` | 16 hücre × 5 program gürültülü sadakatleri | `Bell 0,950` (`min 0,942`), `GHZ4 0,940` (`min 0,926`), `Grov2 P11=0,924`, `QFT3 0,838`, `BF3 0,888` | `0,90/0,88/0,85/0,82/0,80` + `min≥0,85` | **PASS** |
| `P126_8` | 16 hücre `D0(17,5 s)` & paralel `1 µm` yalıtım | `max D0=7,76e-9`, `J(1 µm)=9,50e-9 Hz`, `16×` hızlanma | `≤1e-5`, `<1e-6 Hz` | **PASS** |

**Üç `FAIL` hükmünün dürüst kök-neden tanısı:**
- **`P126_1`:** `u_err = 3,47×10⁻¹²` (geçti) ve tüm `Rx/Ry(π/2)` (`nom 0,9985–0,9997`, `wc 0,9960–0,9988`) ile tüm `cX_XY8_16` nominal (`0,9986–0,9999`, `sp_nom 0,9983–1,0000`) geçti; yalnız tek-kübit `X q2` nominal `0,99423` (`-0,00077`), `X q1` tek seyirci `0,9619` ve en zor `6,89 kHz` hedefi `cX q3` en-kötü tam-fazlı 32B köşesi `0,97264` nedeniyle kayıtlı katı eşik altında kaldı. Tam faz-kilitli `32×32` üniter sadakat, `Exp61`'in sanal-Z popülasyon ölçütünden (`0,9975`) yapısal olarak daha serttir.
- **`P126_2`:** `CNOT` 6/6 çiftte `≥0,9873` ve gürültülü `CZ` ortalaması `0,9444` (`≥0,85`) geçti; yalnız `q3` (`6,89 kHz`) içeren `CZ(2,3)` çifti `0,9828` (`-0,0022`) ve elektron artık sızıntısı `3,61×10⁻³` (`>10⁻³`) ile eşiği hafifçe kaçırdı.
- **`P126_3`:** Analitik FFT varyans kalibrasyonu kesindir (`Var[φ_echo]=2`), ancak `n_traj=512` sonlu Monte Carlo örneklemesinde standart hata `σ_MC ≈ 0,035` olduğundan 8 denemeden 1'i (`F1 α=2`) `1,7σ` sapmayla `0,3087` (`err=0,0592 > 0,05`) verdi (`n_traj=2000` ön testinde `0,3737`, `err=+0,0058`).

---

## 3. Bölüm 1: `Exp62 F1` Evrensel Kapı Kümesi, DDRF Genlik Payı & İki-Kübit `CZ`/`CNOT`/`CCZ`

### 3.1. `F1` Tam 32B Kapı Sentezi (`bound = 15 kHz`, `T = 500 µs`, `M = 64`, `±400 Hz × ±2%`)

| Kapı Ailesi | `nom_32D` (min–maks) | `worst_corner` (min–maks) | `max u_err` (Frobenius) | `sp_ret_nom` (min–maks) | `sp_ovl_448` (min–maks) |
|---|---:|---:|---:|---:|---:|
| `Rx(π/2)` (`q0..q3`, `N_dd=0`) | `0,99852–0,99972` | `0,99601–0,99881` | `7,8×10⁻¹³` | `0,98804–0,99981` | `0,6636–0,9864`* |
| `Ry(π/2)` (`q0..q3`, `N_dd=0`) | `0,99852–0,99972` | `0,99601–0,99881` | `8,4×10⁻¹³` | `0,98805–0,99981` | `0,6633–0,9864`* |
| `X(π)` (`q0..q3`, `N_dd=0`) | `0,99423–0,99766` | `0,97863–0,99301` | `7,3×10⁻¹³` | `0,96194–0,99953` | `0,6199–0,9735`* |
| `cX_XY8_16` (`q0..q3`, `N_dd=16`) | `0,99862–0,99985` | `0,97264–0,99317` | `3,5×10⁻¹²` | `0,99825–0,99998` | `0,99023–0,99954` |

*\*Tek-kübit kapılar (`N_dd=0`) elektron `|0_e⟩` öz durumundayken çalıştığı için `|1_e⟩` dalı boştur; banyo örtüşmesi yalnız iki-dal dolaştırıcı `cX_XY8_16` kapılarında fiziksel olarak aktiftir.*

### 3.2. DDRF Aşırı-İnce Odaklama Çapraz Konuşması & RF Genlik Payı Tanısı (`F1 q3`, `min_gap = 6,89 kHz`)

| Darbe / Strateji | `N_dd` / kapı (`f_mod`) | 32B Nominal Sadakat | En Kötü Seyirci Tutunma | Tüm 448-Seyirci Örtüşmesi |
|---|---:|---:|---:|---:|
| `GAUSS500` (yalın) | `0` (`0 kHz`) | `0,99988` | `0,99981` | `0,99922` |
| `GAUSS500` (yalın) | `2` (`2 kHz`) | `0,99981` | `0,98345` | `0,94879` |
| `GAUSS500` (yalın) | `4` (`4 kHz`) | `0,99921` | `0,88773` | `0,83323` |
| `GAUSS500` (yalın) | `8` (`8 kHz`) | `0,99842` | `0,19359` | `0,20354` |
| `GAUSS500` (yalın) | `16` (`16 kHz`) | `0,98852` | `0,01400` | **`0,000537`** |
| `GAUSS500` (yalın) | `32` (`32 kHz`) | `0,98088` | `0,00089` | **`1,51×10⁻⁶`** |
| `XY8-GRAPE` (`bound = 5 kHz`) | `16` (`16 kHz`) | `0,77156` | `0,99241` | `0,95570` |
| `XY8-GRAPE` (`bound = 10 kHz`) | `16` (`16 kHz`) | `0,99959` | `0,99795` | **`0,99154`** |
| `XY8-GRAPE` (`bound = 15 kHz`) | `16` (`16 kHz`) | `0,99821` | `0,99707` | **`0,99189`** |

### 3.3. Elektron-Aracılı İki-Kübit `CZ(i,j)` / `CNOT(i→j)` & Doğal 3-Cisim `CCZ(0,1,2)` (`F1`)

Exact devre özdeşliği (`4,44×10⁻¹⁶` cebirsel doğruluk): `CΦ(i,j; φ) = Rz_i(φ/2) Rz_j(φ/2) H_i H_j [Rx_e(+π/2) cX_j cX_i Ry_e(-φ/2) cX_i cX_j Rx_e(-π/2)] H_i H_j`.

| Çift `(i,j)` | `CZ` İdeal Süreç `F` | `CZ` Elektron Sızıntısı | `CNOT` İdeal Süreç `F` | `CZ` Gürültülü `F_proc` (`f=%1, α=2, ε=10⁻³`) |
|---|---:|---:|---:|---:|
| `(0, 1)` | `0,99567` | `8,3×10⁻⁴` | `0,99646` | `0,94587` |
| `(0, 2)` | `0,99464` | `1,4×10⁻³` | `0,99454` | `0,94735` |
| `(0, 3)` | `0,99014` | `3,1×10⁻³` | `0,99195` | `0,94837` |
| `(1, 2)` | `0,99311` | `1,1×10⁻³` | `0,99236` | `0,94827` |
| `(1, 3)` | `0,98676` | `3,2×10⁻³` | `0,98981` | `0,94528` |
| `(2, 3)` | `0,98279` | `3,6×10⁻³` | `0,98730` | `0,93140` |
| **Ortalama (6 çift)** | **`0,99052`** | `2,2×10⁻³` | **`0,99207`** | **`0,94442`** |
| **Doğal `CCZ(0,1,2)`** | `0,93379` | `6,7×10⁻³` | — | *(`18,00 ms`: `9,0 ms e_sup`, `36` RF, `288` `XY8`)* |

---

## 4. Bölüm 2: Risk `R3` Kapanışı — İç-İçe `XY8` vs `Exp63` Analitik Model & `XY8` vs `CPMG`

### 4.1. `F1` (`f=%1`, `T2e = 1,269 ms`) `GHZ-4` Sadakati vs `N_total` (`T_tot = 2,0 ms`, `n_traj = 256`)

| `N_total` (`N_dd`/kapı) | İdeal `Q` (448 seyirci) | `sp_ovl448` | 32B `α=1, ε=10⁻³` | `Exp63 α=1` | 32B `α=2, ε=10⁻³` | `Exp63 α=2` | 32B `α=2, ε=10⁻²` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `0` (`0`) | `0,6011` | `0,2096` | `0,4946` | `0,6034` | `0,4996` | `0,6034` | `0,4996` |
| `8` (`2`) | `0,9173` | `0,8502` | `0,7777` | `0,7854` | `0,8865` | `0,8354` | `0,8439` |
| `16` (`4`) | `0,9261` | `0,8608` | `0,8407` | — | `0,9099` | — | `0,8239` |
| **`32` (`8`)** | **`0,9907`** | **`0,9889`** | **`0,9260`** | — | **`0,9648`** | — | `0,7790` |
| **`64` (`16`)** | **`0,9901`** | **`0,9858`** | **`0,9206`** | `0,8851` | **`0,9452`** | `0,9250` | `0,6382` |
| `128` (`32`) | `0,5437` | `0,0972` | `0,5064` | `0,8827` | `0,5071` | `0,9134` | `0,2878` |

### 4.2. Dört `Exp62` Bolluk Finalistinde `N_total = 64` Karşılaştırması (`ε = 10⁻³`, `n_traj = 256`)

| Hücre (`f`) | Seçim Verimi | `T2e` (ms) | `D0(17,5 s)` maks sızıntı | `sp_ovl` | 32B `α=1` (`Exp63`) | 32B `α=2` (`Exp63`) |
|---|---:|---:|---:|---:|---:|---:|
| `F0.5` (`%0,5`) | `%26` | `2,252` | `5,43×10⁻¹¹` | `0,9959` | `0,9298` (`0,9197`) | `0,9358` (`0,9437`) |
| **`F1` (`%1,0`)** | **`%51`** | **`1,269`** | **`5,31×10⁻¹²`** | **`0,9858`** | **`0,9209`** (`0,8851`) | **`0,9433`** (`0,9250`) |
| `F2` (`%2,0`) | `%69` | `0,678` | `4,95×10⁻¹⁰` | `0,9402` | `0,8545` (`0,8243`) | `0,9195` (`0,8900`) |
| `F4.7` (`%4,7`) | `%66` | `0,300` | `2,25×10⁻⁹` | `0,9675` | `0,6755` (`0,7038`) | `0,8955` (`0,8092`) |

*Not:* Gerçek `1/ω^α` Gauss banyosunda doğal bozulma üssü `β = α + 1` (`α=1 → β=2`, `α=2 → β=3`) olduğundan `Exp63`'ün muhafazakâr `β=1` üsteli `F1` ve `F2` noktalarında alt-sınır verir; `F4.7` doğal silisyumda `α=1` hâlâ `< 0,85`'te (`0,6755`) kalır ve `f=%1` (`%51` verim + her iki `α`'da `>0,92` + `sp_ovl=0,986`) sağlam temel çalışma noktası olarak kesinleşir.

### 4.3. `XY8` vs `CPMG` Sistematik Aşırı Dönme Dayanıklılığı (`F1`, `N=64`, `f=%1`, `α=2`)

| `δθ_sys` (mrad) | Eşdeğer 1-darbe `ε` | `GHZ_X` (`XY8` / `CPMG`) | `GHZ_Y` (`XY8` / `CPMG`) | `XY8 − CPMG` Kazancı (`GHZ_Y`) |
|---:|---:|---:|---:|---:|
| `0,00` | `0` | `0,9895` / `0,9895` | `0,9896` / `0,9896` | `+0,0000` |
| `31,62` | `2,5×10⁻⁴` | `0,9865` / `0,8906` | `0,9860` / `0,8935` | `+0,0924` |
| **`63,25`** | **`1,0×10⁻³`** | **`0,9767`** / `0,6454` | **`0,9756`** / `0,6512` | **`+0,3245`** |
| `100,00` | `2,5×10⁻³` | `0,9572` / `0,3317` | `0,9555` / `0,3366` | **`+0,6189`** |

---

## 5. Bölüm 3: 16 Heterojen Silisyum Hücresinde Çok-Hücreli Programlanabilirlik (`f = %1`)

16 bağımsız `f=%1` (`M=452` çekirdekli) sertifikalı hücre (`CELL_00_F1_ANCHOR` + `CELL_01`..`CELL_15`, `min_gap ∈ [6,89; 46,66] kHz`, `A_k CV = %55,6`, tümünde `Lie = 1023/1023`, `D0(17,5 s) ≤ 7,76×10⁻⁹`) üzerine derlenen 5 mantıksal program:

| Mantıksal Program | Süre (`e_sup` / DD) | İdeal 32B Ort. (min) | Statik Köşe Ort. (`±400 Hz × ±%2`) | Gürültülü `α=2, ε=10⁻³` Ort. | Medyan | En Kötü – En İyi (16 Hücre) | Paralel 16-Hücre vs Sıralı |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`Bell`** | `4,50 ms` (`2,0 ms` / `64`) | `0,9950` (`0,9843`) | `0,9563` | **`0,9501`** *(α=1: `0,9282`)* | `0,9513` | `0,9416–0,9538` | `4,50 ms` vs `72,0 ms` (`16×`) |
| **`GHZ-4`** | `2,00 ms` (`2,0 ms` / `64`) | `0,9867` (`0,9713`) | `0,8480` | **`0,9401`** *(α=1: `0,9155`)* | `0,9436` | `0,9263–0,9479` | `2,00 ms` vs `32,0 ms` (`16×`) |
| **`Grover-2`** | `13,00 ms` (`4,0 ms` / `128`) | `0,9724` (`0,9317`) | `0,8985` | **`0,8896`** *(P11: **`0,9237`**)* | `0,8922` | `0,8479–0,9135` *(P11 min `0,9055`)* | `13,0 ms` vs `208,0 ms` (`16×`) |
| **`BitFlip-3`** | `17,50 ms` (`8,0 ms` / `256`) | `0,9710` (`0,9198`) | `0,9164` | **`0,8878`** *(kodsuz `0,0000`)* | `0,8932` | `0,8416–0,9046` | `17,5 ms` vs `280,0 ms` (`16×`) |
| **`QFT-3`** | `14,50 ms` (`6,0 ms` / `192`) | `0,9626` (`0,8597`) | `0,8689` | **`0,8377`** | `0,8445` | `0,7500–0,8644` | `14,5 ms` vs `232,0 ms` (`16×`) |

- **Hücreler arası mikron-adım dipol yalıtımı (`M4` ön-inceleme):** `1 µm` adımda maks dipol bağı `9,50×10⁻⁹ Hz`, `2 µm`'de `1,19×10⁻⁹ Hz`, `5 µm`'de `7,60×10⁻¹¹ Hz`. Her hücre kendi yerel RF taşıyıcı kümesini (`{f_k^(c)}`) kullandığı için 16 hücre ortak `500 µs` / `XY8` saat çatısında sıfır çapraz konuşmayla paralel yürütülür.

---

## 6. Sınırlar & `src/machine_control/pulse_engine.py` Yeniden Kullanım Arayüzü

**Sınırlar:** (1) Elektron MW π darbeleri anlık birim matris (`~50 ns ≪ 7,81 µs` dilim) olarak modellendi; sonlu MW darbe şekli ve AWG analog yükselme süresi açık bırakıldı. (2) Banyo çekirdekleri aktif 4 çekirdekle dipol-bağsız (`2×2` tam seyirci örtüşmesi) olarak katıldı; tam `2^453` çok-cisim banyo dinamiği kapsam dışıdır. (3) `K_sub = 4` aktif alt yazmaç (`32×32`) tam üniter çözüldü; `K=8` tam `512×512` GRAPE sentezi sonraki ölçekleme adımıdır. (4) Fiziksel laboratuvar ölçümü yoktur (`no_lab_measurement=true`).

**Temiz API (`experiments/exp126_atom_cell_programming/`):**
- `hamiltonian126`: `CellSpec`, `load_exp62_finalists()`, `sample_certified_f1_cells()`, `lie_algebra_rank_k4()`, `exact_d0_storage_leakage()`, `sample_bath_noise_hz()`.
- `grape_dd126`: `PulseWaveform`, `CellPulseLibrary`, `dd_schedule()`, `synthesize_gate_grape()`, `synthesize_cell_library()`, `evaluate_gate_32d()`, `propagate_waveform_noisy_32d()`, `run_hahn_echo_32d()`.
- `programs126`: `CompiledProgram`, `emit_cz()`, `emit_cnot()`, `emit_cphi()`, `emit_ccz_012()`, `compile_program()`, `execute_program_32d()`, `evaluate_two_qubit_gate_32d()`.

## 7. Dosya & Doğrulama Envanteri

- Kod: `experiments/exp126_atom_cell_programming/{__init__,hamiltonian126,grape_dd126,programs126,run_exp126,fig_exp126}.py`
- Sonuçlar: `results/exp126_atom_cell_programming/{predictions_exp126.json,exp126.json,summary_exp126.md}`
- Figürler (`1920×1200` PyCairo PNG): `fig_exp126_grape_pulses.png`, `fig_exp126_interleaved_dd_vs_exp63.png`, `fig_exp126_multicell_programs.png`
- Test paketi: `tests/test_exp126.py`
