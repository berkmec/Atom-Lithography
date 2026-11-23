# Exp130 — Risk `R6` Teori & Süreç Kapanışı: Milisaniye Flaş/Lazer Tavlama (`³¹P` Aktivasyonu vs TED Difüzyonu & `²⁹Si` Banyo Karışımı, `H148`)

- **Durum / Karar:** **`PASS`** (`6/6` ön-kayıtlı öngörü `EA1–EA6` geçti; `no_lab_measurement = true`).
- **Epistemik Kapsam:** `{Model}` + `{Sayısal-Simülasyon}` + `{Literatür}` (`Glassbrenner & Slack 1964`, `NIST-JANAF`, `Jellison & Modine 1982/1994`, `Fahey et al. RMP 1989`, `Bracht et al. PRL 1998`, `Stolk et al. JAP 1997`, `Cowern et al. PRL 1999`, `Olson & Roth MSR 1988`, `Exp108 doi:10.1063/1.331355`). Bu deney **Risk `R6`'nın kuramsal, sayısal ve donanım-şartname kapanışını** sağlar; fiziksel tek-donör ms-flaş laboratuvar doğrulaması `M1 G4` donanım kapısı olarak açık kalır (`no_lab_measurement = true`).
- **Kod ve Çıktı Dosyaları:**
  - `experiments/exp130_flash_anneal_diffusion/heat_ted_solver.py`
  - `experiments/exp130_flash_anneal_diffusion/run_exp130.py`
  - `experiments/exp130_flash_anneal_diffusion/plot_exp130.py`
  - `results/exp130_flash_anneal_diffusion/predictions_exp130.json`
  - `results/exp130_flash_anneal_diffusion/exp130.json`
  - `results/exp130_flash_anneal_diffusion/fig_exp130_anneal_window.png`
  - `results/exp130_flash_anneal_diffusion/fig_exp130_profiles_ted.png`
  - `tests/test_exp130.py`

---

## 1. Ön-Kayıtlı Öngörü Değerlendirmesi (`H148`: `EA1–EA6`)

| ID | Kriter | Ölçülen / Hesaplanan Sonuç (`{Sayısal-Simülasyon}`) | Karar |
| :--- | :--- | :--- | :--- |
| **`EA1`** | `Exp108` (`doi:10.1063/1.331355`) yeniden üretimi | `600 °C/10 dk` UHV: ön-yüzey birikimi **`%93,2`** (`≥ %15`), vakum kaçışı **`%0,06`** (`< %5`); `800 °C/10 dk` UHV: vakum kaçışı **`%52,7`** (`≥ %30`); kütle koruma hatası **`6,33×10⁻¹⁵`** | **PASS** |
| **`EA2`** | 1B doğrusal-olmayan termal PDE yakınsaması & akı | Izgara/zaman yakınsaması **`%0,184`** (`< %1`), enerji koruma hatası **`%0,0033`** (`< %0,5`); `808 nm / 1,0 ms` `T_peak = 1440,3 K` (`< 1552 K`), `F = 41,15 J/cm²` (`[10, 45]`), `t_quench(<900 K) = 0,333 ms` (`< 10 ms`), `T_back = 592,9 K` (`< 700 K`) | **PASS** |
| **`EA3`** | Geleneksel fırın (`600–800 °C/10 dk`) & RTA (`1000 °C/10 s`) başarısızlığı | Fırın `600 °C` (`σ = 6,11 nm`, kayıp `%9,0`), Fırın `800 °C` (`σ = 3,13 nm`, kayıp `%4,4`), RTA `1000 °C/10 s` (`σ = 4,97 nm`, kayıp `%21,2`) — tümü ortak pencereden **KALIR** | **PASS** |
| **`EA4`** | Erimeden çalışan kesintisiz `ms`-flaş süreci | Sıkı (`σ ≤ 0,50 nm`) kesintisiz pencere: `t_pulse ∈ [0,077, 12,92] ms`, `T_peak ∈ [1223,6, 1543,6] K` (`32/42` kutu noktası PASS); optimal `808 nm 1,0 ms / 1440 K`: **`f_act = %99,98`**, **`σ_anneal = 0,328 nm`**, **kayıp `%0,022`**, **`σ_iso = 0,0314 nm`** | **PASS** |
| **`EA5`** | `Exp124 Arch-B` bütçesi & `20 mK` kriyo toparlanma | `Exp124 Arch-B` toplam konum belirsizliği **`σ_tot = 3,655 nm`** (baz `3,674 nm`'den iyi, tavan `3,80 nm`); Debye kriyo toparlanma: `16×16 mm` aktif alan **`3,18 dk`** (`≤ 15 dk`), `50 mm` tam pul **`11,03 dk`**, hat-içi RT yükleme kilidi **`0,00 dk / 0 J`** | **PASS** |
| **`EA6`** | `S5.5` CF63 safir optik uyumu & `LIDT` emniyeti | `CAD v3.0` `Ø44 mm` temiz açıklık (`Ø36 mm` demet, `4 mm` radyal pay); `T_uncoated = %85,9` (`≥ %85`), `T_AR = %98,0` (`≥ %97`); `100 J/cm²` muhafazakâr `1 ms` safir `LIDT` tabanına göre emniyet payı **`9,47×`** (`16×16 mm` AR), **`8,30×`** (kaplamasız), **`3,36×`** (`1:1` kolime `0,5 ms`) | **PASS** |

---

## 2. Birleşik Fizik Modeli ve Yakınsama Doğrulaması

### 2.1. 1B Doğrusal-Olmayan Si Termal İletim PDE'si (`{Model}` + `{Sayısal-Simülasyon}`)

- `500 µm` kristal Si pul üzerinde gerilmiş sonlu-hacim ızgarası (`dz_0 = 50 nm` yüzeyden `500 µm` arka yüze `n_cells = 80 / 120 / 160`), `Glassbrenner–Slack / NIST-JANAF` PCHIP `k_Si(T)` (`148 → 22 W/(m·K)`) ve `c_p(T)` (`712 → 1038 J/(kg·K)`), `Jellison–Modine` sıcaklığa bağımlı Beer–Lambert soğurması (`308 / 532 / 808 nm`), Stefan–Boltzmann ön/arka ışınım kaybı (`ε = 0,65`) ve Picard yinelemeli örtük zaman entegrasyonu çözüldü.
- **Yakınsama ve Enerji Korunumu (`808 nm, 1,0 ms, F = 41,15 J/cm²`):**

| Izgara (`n_cells, n_steps`) | `T_peak` (K) | `T_back,max` (K) | `t_quench(<900 K)` (ms) | Enerji Dengesi Bağıl Hatası |
| :--- | :--- | :--- | :--- | :--- |
| `(80, 40)` | `1439,83` | `592,85` | `0,3629` | `3,27×10⁻⁵` |
| `(120, 80)` *(Referans)* | `1440,26` | `592,88` | `0,3331` | `9,62×10⁻⁶` |
| `(160, 160)` | `1442,91` | `592,90` | `0,3422` | `3,81×10⁻⁶` |

- `120 → 160` göreli `T_peak` farkı **`%0,184`** (`< %1`), tüm çözümlerde enerji dengesi hatası **`≤ 3,3×10⁻⁵`** (`%0,0033 << %0,5`).

### 2.2. Denge-Dışı TED / Kick-Out, Yüzey Kaçışı ve `²⁸Si/²⁹Si` Öz-Difüzyon PDE'si (`{Model}` + `{Literatür}`)

- `z ∈ [0, 60 nm]` derinliğinde (`dz = 0,40 nm`, `100/150/200` ızgara yakınsaması **`%0,018`**, toplam kütle koruma hatası **`~10⁻¹⁵`**) dört bağlı alan eşzamanlı çözüldü:
  1. `³¹P` yerel katı-faz epitaksi (`SPE`) aktivasyonu: `Olson & Roth (1988)` Si(100) hızı `v_0 = 3,68×10⁸ cm/s`, `E_a = 2,70 eV`, hasarlı katman derinliği `L_regrow = 10,0 nm` (`ν_act = 3,68×10¹⁴ s⁻¹`).
  2. Si öz-arayer (`I`) küme salımı (`Stolk 1997 / Cowern 1999`, `E_diss = 3,10 eV`), yüzey rekombinasyon sınırı (`L_surf = 2,0 nm`) ve **boyutluluk fiziği**:
     - Yüksek doz 1B düzlemsel örtü (`doi:10.1063/1.331355`, `~10¹⁵ cm⁻²`): komşu şelaleler yanal örtüştüğünden `I` yalnızca dikey `z = 0` yüzeyine kaçar (`r_casc = None`).
     - Makinenin tekil `5 keV ³¹P⁺` donör implantasyonu (`Rp = 6,46 nm`, `σ_z = 2,88 nm`, `Exp92`): komşu donörlerden `≥ 20 nm` izole, `r_casc = 2,5 nm` yarıçaplı tekil şelaleden 3B radyal `I` kaçışı (`k_rad = 4 D_I / r_casc²`) zaman-integralli aşırı-doygunluğu ~`43×` düşürür.
  3. `Fahey (1989)` `D_P^eq = 3,85 exp(-3,66 eV/kT) cm²/s` (`f_I = 0,95`) + `Bracht (1998)` `D_I C_I*/C_Si = 2980 exp(-4,95 eV/kT) cm²/s` (`E_f = 3,18 eV, E_m = 1,77 eV`): **negatif TED aktivasyon enerjisi** (`E_SD,I - E_a,P = +1,29 eV`) nedeniyle sıcaklık `600 °C → 1167 °C` çıktıkça TED yayılımı dramatik biçimde bastırılırken `2,70 eV` SPE aktivasyonu üstel hızlanır.
  4. Ön-yüzey `P` segregasyon tuzağı (`L_trap = 0,5 nm`) + UHV ısıl desorpsiyonu (`E_evap = 3,10 eV`) ve `Bracht (1998)` `²⁸Si/²⁹Si` öz-difüzyonu (`530 exp(-4,75 eV/kT) cm²/s`, `z_epi = 20 nm` Mod B `%1 ²⁹Si` banyo arayüzü).

---

## 3. `Exp108` Çapa Doğrulaması, Geleneksel Tavlama ve Dalga Boyu Karşılaştırması

| Süreç / Dalga Boyu | `t_pulse` | `T_peak` (K) | Akı `F` (J/cm²) | `f_act` (%) | Yüzey + Vakum Kaybı (%) | `σ_anneal` (nm) | `σ_iso` (nm) | `Exp124 σ_tot` (nm) | Pencere (`≤0,5 nm`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Exp108` 1D Örtü `600 °C` UHV | `600 s` | `873,2` | — | `6,73` | **`93,21` birikim + `0,06` kaçış** | `78,31` | — | — | **Çapa (EA1)** |
| `Exp108` 1D Örtü `800 °C` UHV | `600 s` | `1073,2` | — | `33,40` | `13,88` birikim + **`52,72` kaçış** | `33,77` | — | — | **Çapa (EA1)** |
| Fırın `600 °C / 10 dk` (Tekil P) | `600 s` | `873,2` | — | `91,03` | `8,98` | `6,109` | `0,0407` | `7,111` | **FAIL** |
| Fırın `800 °C / 10 dk` (Tekil P) | `600 s` | `1073,2` | — | `95,58` | `4,42` | `3,133` | `0,0689` | `4,803` | **FAIL** |
| RTA `1000 °C / 10 s` (Tekil P) | `10 s` | `1273,2` | — | `78,78` | `21,22` | `4,969` | `0,3999` | `6,159` | **FAIL** |
| `308 nm` Excimer (`50 µs`) | `0,05 ms` | `1440,8` | `15,40` | `49,96` | `0,001` | `0,108` | `0,0097` | `3,642` | **FAIL (`f_act`)** |
| `308 nm` Excimer (`1,0 ms`) | `1,0 ms` | `1440,5` | `68,74` | `99,98` | `0,022` | `0,329` | `0,0315` | `3,655` | PASS *(yüksek F/UV)* |
| `532 nm` Yeşil/Xe (`1,0 ms`) | `1,0 ms` | `1440,4` | `43,67` | `99,98` | `0,022` | `0,329` | `0,0314` | `3,655` | **PASS (Yedek)** |
| `808 nm` Diyot (`0,5 ms`) | `0,5 ms` | `1440,8` | `29,17` | `99,88` | `0,013` | `0,268` | `0,0260` | `3,650` | **PASS (Kompakt)** |
| **`808 nm` Diyot (`1,0 ms`, Önerilen)** | **`1,0 ms`** | **`1440,3`** | **`41,15`** | **`99,98`** | **`0,022`** | **`0,328`** | **`0,0314`** | **`3,655`** | **PASS (Optimum)** |
| `808 nm` Diyot (`1,5 ms`) | `1,5 ms` | `1439,8` | `50,16` | `99,97` | `0,029` | `0,361` | `0,0340` | `3,658` | PASS |
| `808 nm` Diyot (`2,0 ms`) | `2,0 ms` | `1439,3` | `57,52` | `99,97` | `0,035` | `0,385` | `0,0357` | `3,660` | PASS |

- **Neden `808 nm` `1,0 ms` Birincil Seçimdir?** Si'nin `808 nm`'de en düşük yansıtması (`R = 0,33`, `308 nm`'de `0,60`) en düşük akıyı (`41,15 J/cm²`) verir; UV safir renk-merkezi hasarı sıfırdır; ticari qCW diyot çubuk istifleri `%50` duvar-prizi verimliliğiyle darbe-içi `≤ ±%2` düz-tepe kararlılık sunar. `532 nm` (`43,67 J/cm²`) eşdeğer performanslı yedek seçenektir.

---

## 4. Duyarlılık ve Belirsizlik (`UQ`) Stres Testleri (`808 nm, 1,0 ms, 1440 K`)

| Stres Senaryosu (`{Sayısal-Simülasyon}`) | `T_peak` (K) | `f_act` (%) | `σ_anneal` (nm) | Kayıp (%) | `σ_iso` (nm) | `Exp124 σ_tot` (nm) | Durum |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Nominal (`41,15 J/cm², C_cl=3×10¹⁹, r=2,5 nm`) | `1440,3` | `99,98` | `0,328` | `0,022` | `0,0314` | `3,655` | **PASS (`≤0,5 nm`)** |
| Akı `-%5` sapma (`39,09 J/cm²`) | `1361,5` | `97,50` | `0,275` | `0,010` | `0,0196` | `3,650` | **PASS (`≤0,5 nm`)** |
| Akı `+%5` sapma (`43,21 J/cm²`) | `1519,0` | `99,94` | `0,379` | `0,056` | `0,0474` | `3,660` | **PASS (`≤0,5 nm`)** |
| Yavaş SPE (`0,5× ν_act`, `L_regrow=20 nm`) | `1440,3` | `99,87` | `0,328` | `0,019` | `0,0314` | `3,655` | **PASS (`≤0,5 nm`)** |
| Geniş şelale (`r_casc = 4,0 nm`) | `1440,3` | `99,95` | `0,481` | `0,048` | `0,0445` | `3,672` | **PASS (`≤0,5 nm`)** |
| `3×` arayer hasarı (`C_cl = 9×10¹⁹ cm⁻³`) | `1440,3` | `99,95` | `0,550` | `0,047` | `0,0510` | `3,681` | **PASS (`≤1,0 nm` & `≤3,80 nm`)** |
| 1D yüksek-doz örtü üst sınırı (`r_casc = None`) | `1440,3` | `98,93` | `1,989` | `1,066` | `0,1426` | `4,148` | Üst sınır *(yalnız yüksek-doz)* |

> **Önemli `M1 G4` Laboratuvar Çıkarımı:** `±%5` lazer akı gürültüsü, `2×` yavaş SPE ve `r_casc = 4 nm` geniş şelale altında dahi tüm `4` ölçüt sıkı `≤ 0,50 nm` hedefiyle sağlanır. Ancak yüksek-doz `1D` örtü testi (`r_casc = None`) `1,99 nm` verir; dolayısıyla `M1 G4` laboratuvar doğrulaması yüksek-doz örtü pulu yerine düşük-doz izole tek-donör implantasyonu (`≤ 10¹¹ cm⁻²`, aralık `≥ 20 nm`) üzerinde yapılmalıdır.

---

## 5. `S5.5` Flaş/Lazer Tavlama Optik Donanım Şartnamesi (`CAD v3.0/v4.0` & `BOM/RFQ`)

`CAD v3.0` (`research/atom_lithography_machine/cad/params.py` L437–444) geometrisiyle doğrudan uyumlu şartname (`{Model}` + `{Varsayım}`):

| Parametre | Kilitlenen `S5.5` Şartnamesi | Uyum / Emniyet Payı |
| :--- | :--- | :--- |
| **Port & Geometrik Zarf** | Ekvatoral `+Y` portu (`Z_WAFER = 500,0 mm`), CF63 UHV fırınlanabilir tek-kristal safir (`Al₂O₃`) pencere (`Ø50 mm × 8,0 mm`), kanal temiz açıklığı **`Ø44,0 mm`**, dış kafa zarfı `84 × 88 × 84 mm` | Demet çapı pencere düzleminde **`Ø36,0 mm`** → **`4,0 mm`** radyal kırpılma payı (`CAD v3.0` revizyonu gerekmez) |
| **Optik Kaynak** | **`808 nm`** qCW makro-kanallı diyot-lazer bar istifi (19" harici raf + fiber demeti → `S5.5` homojenleştirici/röle kafası); yedek `532 nm` | `1,0 ms` düz-tepe darbe (`%10` çıkış / `%80` plato / `%10` iniş), çip üstü tekdüzelik `≤ ±%2` |
| **Pul Üstü Akı & Sıcaklık** | **`41,15 J/cm² ± %5`** (`29,17 J/cm²` @ `0,5 ms` düşük-akı seçeneği); **`T_peak = 1440,3 K` (`1167,1 °C`)** | Erime noktasının (`1687 K`) **`246,7 K`** altında (`0,854 T_melt < 0,92 T_melt`), arka yüz max **`592,9 K`**, `< 900 K` sönüm **`0,333 ms`** |
| **Safir Pencere İletimi & `LIDT`** | `n(808 nm) = 1,760` → **`T_uncoated = %85,9`**, **`T_AR = %98,0`**; toplam optik zincir verimi **`%93,14`**; muhafazakâr `1 ms` `LIDT` tabanı **`100 J/cm²`** (tipik kaplamasız `250 J/cm²`, ISO 21254 içsel ölçekleme `3162 J/cm²`) | **Mod 1 (`16×16 mm` tek atış):** `E_wafer = 105,3 J`, `E_src = 113,1 J`, `P_peak = 125,7 kW`, **`F_win = 10,56 J/cm²` (AR)** → **`9,47×`** `LIDT` payı (`8,30×` kaplamasız) |
| **Alternatif Teslimat Modları** | **Mod 2 (`4×4 mm` adım-flaş, 16 dikişli kare — kompakt BOM):** `E_src = 7,07 J`, **`P_peak = 7,85 kW`**, `F_win = 0,66 J/cm²` (`151,5×` `LIDT` payı). **Mod 3 (`1:1` kolime `0,5 ms`):** `F_win = 29,77 J/cm²` (`3,36×` `LIDT` payı) | **Mod 4 (Hat-İçi RT Yükleme Kilidi — Üretim Bazı):** Aynı `808 nm / 1,0 ms` reçete oda sıcaklığı UHV yükleme kilidinde uygulanır → **`0 J` kriyo yük, `0,00 dk` DR kaybı** |
| **Yerinde (`S5.5`) Kriyo Toparlanma (`20 mK`)** | `50 mm` Si pul (`2,29 g`) + `0,15 kg` OFHC-Cu/AlN taşıyıcı, `PT410` `4 K` ısıl anahtar (`1,0 W`), Still (`30 mW`), MXC (`540 → 19 µW`) + `120 s` yerleşme payı | `4×4 mm` kare: **`2,08 dk`** (`4,4 J`, `19,8 K`); `16×16 mm` aktif alan: **`3,18 dk`** (`70,6 J`, `39,9 K`); `50 mm` tam pul: **`11,03 dk`** (`541 J`, `71,4 K`) — hepsi `≤ 15 dk` |
| **Diyagnostik & Güvenlik Kilitleri** | Dikroik ayırıcı üstünden hızlı iki-renkli InGaAs/Si pirometre (`10 µs`, `900–1700 K`), hat-içi fotodiyot enerji integratörü (`±%1,5` kapalı çevrim), MXC `< 1 K` & UHV sürgülü vana donanım deklanşör kilidi | Atış-bazlı akı sapmasını `±%1,5` içine kilitleyerek `±%5` süreç penceresinde `>3×` kontrol payı sağlar |

---

## 6. Görsel Doğrulama ve `Exp124` Etkisi

- `results/exp130_flash_anneal_diffusion/fig_exp130_anneal_window.png`: `(t_pulse, T_peak)` 2B süreç faz diyagramı (`10 µs .. 600 s × 700 .. 1660 K`), `808 nm` termal akı/arka-yüz ölçeklemesi ve `Exp124 Arch-B` konumlandırma bütçesi karşılaştırması (**`3,655 nm`** vs baz `3,674 nm` ve tavan `3,800 nm`).
- `results/exp130_flash_anneal_diffusion/fig_exp130_profiles_ted.png`: 5 panelli teknik pano — (A) `808/532/308 nm` 1B doğrusal-olmayan termal dalga formları, (B) `Exp108` `doi:10.1063/1.331355` kütle-kaderi doğrulaması, (C) `5 keV ³¹P⁺` derinlik profilleri, (D) `z_epi = 20 nm` Mod B `²⁸Si/²⁹Si` arayüz koruması (`σ_iso = 0,0314 nm`), (E) `20 mK` Debye kriyo toparlanma süreleri.
- **Sonuç:** Risk `R6`'nın teori, birleşik PDE süreci ve `S5.5` optik donanım tasarımı **`PASS` (`6/6`)** ile kapatılmıştır. Fiziksel doğrulama adımı (düşük-doz tek-donör `5 keV ³¹P⁺` pulda `808 nm / 1,0 ms / 41,2 J/cm²` sonrası SIMS + 4-nokta/ESR aktivasyon ölçümü) `M1 G4` laboratuvar kapısı olarak kayıtlıdır (`no_lab_measurement = true`).
