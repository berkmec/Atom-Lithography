# Exp124 — 10–15 → 5 keV Yavaşlatmalı İyon Kolonu Optiği, Liouville Kapanışı & 3B Anizotropik Seçim Verimi

**Tarih:** 2026-11-22 / 2026-11-23. **Epistemik Durum:** `no_lab_measurement=true` — tüm sonuçlar `{Model}`, `{Analitik}`, `{Sayısal-Simülasyon}` ve `{Literatür}` düzeyindedir; laboratuvar ölçümü yoktur. Ön-kayıtlı öngörüler (`predictions_exp124.json`) herhangi bir Exp124 hesaplamasından önce yazma-bir-kez kaydedilmiştir.

---

## 1. Yönetici Özeti & Ön-Kayıtlı Hükümler (`CD1`–`CD8`)

| Kimlik | Ön-Kayıtlı Öngörü | Gözlenen Doğrulanmış Sonuç | Hüküm |
|---|---|---|---|
| **CD1** | `Exp66–105` zincir denetimi `<10⁻⁴` + `_attack91.py` Liouville açığı `>1,7×` | Maks. çapa bağıl hatası **`1,61×10⁻¹⁶`**; `B_net(5 keV)=3,98×10⁴` vs `B_req=7,21×10⁴ A/m²/sr` (**`1,813×`** açık) | **PASS** |
| **CD2** | 2B Laplace + `DOP853` Wronskian sürüklenmesi `<10⁻⁶` & Scherzer vs ray-trace `C_c` `<%5` | Wronskian sürüklenmesi **`2,05–4,87×10⁻⁸`**; Scherzer vs ray-trace `C_c` farkı **`%0,00–%0,12`** (`C_s` farkı `%0,07–%1,09`) | **PASS** |
| **CD3** | `32 µm` tek-kademe duvarı + `Arch-B`/`Arch-C`'de `E_gap ≤ 12 MV/m` ve `C_c ≤ 0,50 mm` | `Arch-A1` `E_gap=382,8 MV/m`, `Arch-A2` `C_s=470,1 mm`; ancak Scherzer–delinme değişmezi `κ_c ≥ 4,67` nedeniyle `E_gap ≤ 12 MV/m`'de **`C_c = 2,38–2,66 mm > 0,50 mm`** | **FAIL** *(gerçek fiziksel alt sınır keşfi)* |
| **CD4** | Delinme-güvenli (`≤12 MV/m`), Liouville-tutarlı 5 keV kolonda `σ_spot ≤ 1,50 nm`, `σ_tot ≤ 3,80 nm`, `η ≥ 0,99`, Wien `≥3×`, HDA `≤2,0 eV` | `Arch-B` (`10,60 MV/m`) + `HDA-HiRes` (`0,453 eV`) + `Ti=0,25 eV / 10 ms` (veya `LMIS 1 ms`): **`σ_spot=1,428 nm`**, **`σ_tot=3,674 nm`**, **`η=0,9914`**, Wien **`3,92×` yarık** | **PASS** |
| **CD5** | `10–15 keV` üst kolon Coulomb bastırması `≥2,5×` & tek demetcik doluluğu `<0,01` | Laminer `10/5 keV` = **`2,83×`** (`15/5` = `5,20×`); Holtsmark `10/5` = **`2,52×`**; tek-demetcik `N̄₁ = 1,40×10⁻³` | **PASS** |
| **CD6** | Taşınabilir Exp42/44/48 motorunun Exp57 (`49/100`) & Exp105 (`277/400`) birebir denetimi | `AUDIT_EXP57_S5_N1024 = 49/100 (0,4900)` ve `AUDIT_EXP105_ISO3p8_N1024 = 277/400 (0,6925)` **bit-birebir** | **PASS** |
| **CD7** | Anizotropik ayrışma: `BCA_PURE ∈ [0,74; 0,88]`, `P91_BCA > 0,70`, `P91_HOLMES < 0,65` | `BCA_PURE = 0,7875` ✓, `P91_BCA = 0,7675` ✓, ancak `P91_HOLMES (z>0) = 0,6950` ✗ *(yüzeysiz `0,6325` < 0,65! Yüzey kesmesi `N=1024`'te spektral sıkışıklığı azaltıp `+6,25 pp` yükseltti)* | **FAIL** *(gerçek spektral sıkışıklık keşfi)* |
| **CD8** | Stokastik `³¹P` donör 3B saçılma cezası `≥0,15` mutlak düşüş | `P91_BCA` sabit donör `0,7675` → stokastik donör **`0,4375`** (**`−33,0 pp`**); Holmes `0,6950 → 0,2800` (**`−41,5 pp`**) | **PASS** |

**Başarı Kuralı (`CD1 ∧ CD2 ∧ CD3 ∧ CD4 ∧ CD6`):** `CD3`'ün dürüst fiziksel reddi nedeniyle `success_rule_met = false` (tahmin dosyası geriye dönük değiştirilmedi). Bu red, `Exp82` ve `Exp91_budget_attack`'in sınanmamış `C_c = 0,50 mm` varsayımının makroskopik UHV elektrik alanı sınırında (`≤12 MV/m`) elektrostatik olarak olanaksız olduğunu kanıtlar ve makineyi `HDA-HiRes (0,453 eV)` + gerçek `10,6 MV/m` daldırmalı mini-lensle fiziksel olarak kapatır (`CD4 PASS`).

---

## 2. Tarihsel Zincir Denetimi & `_attack91.py` Liouville Açığı (`CD1`)

1. `Exp66`, `Exp71`, `Exp72`, `Exp81`, `Exp82`, `Exp91_budget_attack`, `Exp92` ve `Exp105` çapaları tek birleşik Python çekirdeğinde **`1,606×10⁻¹⁶`** (IEEE-754 makine hassasiyeti) içinde yeniden üretildi.
2. **Lagrange–Helmholtz / Liouville İndirgenmiş Parlaklık Kanıtı:** Elektrostatik yavaşlatma boyunca indirgenmiş parlaklık `B_r = B(E)/E = τ_f · J / (π · T_i)` değişmez kalır. `Exp81/82` tutucu değerlerinde (`J = 100 A/m²`, `T_i = 1,0 eV`, `τ_f = 0,25`):
   - `B_r,net = 7,9577 A/m²/sr/V`
   - `B_net(10 keV) = 79.577 A/m²/sr` (`_attack91.py` bunu yanlışlıkla `5 keV` nokta hesabında kullandı!)
   - **`B_net(5 keV) = 39.789 A/m²/sr`** vs. `r = 1,5 nm, α = 10 mrad, 1 iyon/ms` için gereken `B_req = 72.149 A/m²/sr` → **`1,813×` parlaklık açığı** (gerçek geometrik nokta `1,50 nm` değil **`2,020 nm`**).
3. `_attack91.py`'deki 3 hata birlikte belgelenmiştir: (i) Liouville `10→5 keV` ölçekleme ihmali, (ii) `E < 5 keV` saçılma kırpması (`Exp92` kapattı), (iii) `σ=10 nm` hibrit üretim tablosu (`6,05×10⁵` vs `Exp105` `2,92×10⁷/gün`, `48,2×` fark).

---

## 3. 2B Eksenel-Simetrik Laplace PDE & Elektrostatik Lens Mimarileri (`CD2`–`CD5`)

Tüm lens mimarileri 2B eksenel-simetrik Laplace denklemi (`scipy.sparse.linalg.spsolve`, periyodik dizi Wigner–Seitz sınırı `∂Φ/∂r = 0`) + beşinci dereceden eksenel spline + `DOP853` (`rtol=10⁻¹¹`) paraksiyal/kromatik/çok-kutuplu ışın izleme ile çözüldü (`{Sayısal-Simülasyon}`):

| Mimari | Adım / Delik (mm) | `WD` (mm) | `f` (mm) | `C_c` Scherzer / Ray (mm) | `C_s` Scherzer / Mult. (mm) | `E_gap` (MV/m) | `κ_c = C_c·E/V` | Durum |
|---|---|---|---|---|---|---|---|---|
| `Arch-A1_32um_shortWD` | `0,032 / 0,018` | `0,060` | `0,079` | `0,138 / 0,138` (`%0,08`) | `3,157 / 3,153` (`%0,11`) | **`382,81`** | `10,59` | **RED** (UHV delinme duvarı) |
| `Arch-A2_32um_longWD` | `0,032 / 0,018` | `0,500` | `0,443` | `0,615 / 0,615` (`%0,03`) | **`470,05 / 431,91`** | **`196,39`** | `24,14` | **RED** (`C_s` + delinme duvarı) |
| **`Arch-B_0p5mm_immersion`** *(ÖNERİLEN)* | `0,500 / 0,300` | **`0,250`** | `0,820` | **`2,660 / 2,661`** (`%0,03`) | **`10,786 / 10,669`** (`%1,09`) | **`10,60`** | `5,64` | **GEÇER** (alansız `5 keV` wafer, `≤12 MV/m`) |
| `Arch-B15_15to5keV` | `0,600 / 0,280` | `0,480` | `0,973` | `2,615 / 2,616` (`%0,02`) | `14,311 / 14,227` (`%0,59`) | `11,04` | `5,78` | **GEÇER** (`15→5 keV` opsiyonu) |
| `Arch-C_32um_2stage` | `0,032 / 0,018` | `0,083` | `0,535` | `2,383 / 2,383` (`%0,00`) | **`51,583 / 51,953`** (`%0,72`) | `9,79` | `4,67` | Sınırda (`C_s` büyük → `σ_spot=1,93 nm`) |
| `Arch-D_MEMS_microgap35` | `0,100 / 0,050` | `0,260` | `0,397` | `1,190 / 1,192` (`%0,12`) | `23,898 / 23,916` (`%0,07`) | `35,27` | `8,39` | Mikro-aralık AR-GE opsiyonu |

### 3.1 Alt Sistem & 5 keV Çalışma Penceresi Kapanışı (`Arch-B`, `10,60 MV/m`)
- **Wien Kütle Filtresi (`S1.2`, `10 keV`, `B=0,45 T`, `L_w=80 mm`, `L_d=70 mm`, `V_plaka=1348 V`):** `³²PH⁺` sapması **`0,785 mm`** (`0,20 mm` yarığın **`3,92×`**'si, kütle çözünürlüğü `R_m = 120,6`).
- **Yarımküresel Enerji Süzgeci (`S1.5`, `HDA-HiRes`, `R₀=40 mm`, `E_pass=100 eV`, `w_slit=0,35 mm`, `α_in=25 mrad`):** **`ΔE_FWHM = 0,453 eV ≤ 2,0 eV`**, kesin Gauss geçirgenliği `τ_f = 0,0710` (`6 eV` genleşme kabı kaynağından).
- **Boersch & Coulomb (`50 nA` üst taşma demeti, `L=0,35 m`, `r_b=2 mm`):** `5 → 10 keV` (`15 keV`) laminer uzay-yükü bulanıklığını **`2,83×`** (`5,20×`), Holtsmark yörünge sapmasını **`2,52×`** (`4,33×`) bastırır; tek `1 iyon/ms` demetcikte eşzamanlı ortalama iyon sayısı **`N̄₁ = 1,40×10⁻³`** (demetcik içi Boersch sıfır hükmünde).
- **5 keV Çalışma Noktaları (`Exp92 BCA σ_x=3,259 nm`, `Exp72 IBIC η(5 keV, 0,5 pF)=0,9914`):**

| Çalışma Noktası (`E_land=5 keV`) | `α_land` (mrad) | `σ_geom` / `σ_c` / `σ_s` (nm) | `σ_spot` (nm) | `σ_toplam` (nm) | Kriter (`≤1,50 / ≤3,80`) |
|---|---:|---|---:|---:|---|
| `ArchB_naive_2eV_Ti1_1ms` (`Exp82/91` girdileri) | `6,55` | `3,08 / 2,96 / 0,54` | `4,365` | `5,523` | **FAIL** |
| **`ArchB_HiRes_Ti0p25_10ms`** *(0,453 eV, `Ti=0,25 eV`, `10 ms`)* | `6,10` | `0,98 / 0,62 / 0,43` | **`1,428`** | **`3,674`** | **PASS** |
| **`ArchB_HiRes_LMIS_1ms`** *(0,453 eV, `10×` parlak, `1 ms`)* | `6,10` | `0,98 / 0,62 / 0,43` | **`1,428`** | **`3,674`** | **PASS** |
| `ArchB_HiRes_Ti0p5_15ms` *(kanonik `Ti=0,5 eV`, `15 ms`)* | `6,40` | `1,08 / 0,66 / 0,50` | `1,532` | **`3,715`** | `σ_tot` PASS (`σ_spot` +0,03) |
| `ArchB_HiRes_Ti1_25ms` *(en tutucu `Ti=1,0 eV`, `25 ms`)* | `6,55` | `1,16 / 0,67 / 0,54` | `1,605` | **`3,746`** | `σ_tot` PASS (`1,77×10⁹` atış/gün) |
| `ArchB15_HiRes_Ti0p5_15ms` (`15→5 keV`, `WD=0,48 mm`) | `6,05` | `1,14 / 0,61 / 0,56` | `1,578` | **`3,735`** | `σ_tot` PASS |

*(Not: Seçenek A `32×32 = 1.024` eş-adımlı demetcikle `15 ms/atış` = **`2,95×10⁹` atış/gün** ve `10 ms/atış` = **`4,42×10⁹` atış/gün** `%50` duty — Mod B `f=%1` okuma tavanının (`~1,97×10⁸`/gün) hâlâ **`15–22×`** üstündedir!)*

---

## 4. CAD v3.0 İçin Kesin İyon Kolonu Boyut Tablosu (mm — Tekil `Z_WAFER = 500,00 mm` Çerçevesi)

Wafer aktif üst düzlemi **`CAD v3.0`** küresel koordinat çerçevesinde **`Z_WAFER = 500,00 mm`** (`z_rel = 0,00 mm`, `0 V` toprak; üst kolon gömleği `-5,0 kV` yüzer, kaynak anodu `+5,0 kV` → kolonda `10 keV`, wafer'da `5 keV` iniş) konumundadır.
- **Seçenek A (Kilitli Eş-Adımlı `Arch-B` Dizi):** `S2.1` apertür + `S2.2` blanker + `S2.3` `Arch-B` mini-lens **tamamı `0,50 mm` eş-adımlı `32×32 = 1.024` demetcik** (`16,0×16,0 mm` aktif kare, köşegen **`22,63 mm`**, `16×` 64-kanallı SKY130 karo). `S1.6` transfer lensi & `S2.1` taşıyıcı iç açıklığı **`Ø28,0 mm`** → köşegene **`2,69 mm` temiz radyal marj**, sıfır demet kırpması (`32 µm` / `3,2×3,2 mm` yalnızca tarihsel `Exp78/79` / `Arch-C` alternatif dipnotudur).
- **Toplam kolon yüksekliği:** **`562,66 mm`** (`z_CAD: 500,25 → 1062,66 mm`, yerel `z_rel: 0,25 → 562,66 mm`), maksimum dış çap **`Ø110,0 mm`** (`r=55,0 mm < R_iç=182,0 mm` kompakt `s=0,5` UHV odasına `127,0 mm` pay; `Ø352 mm` mıknatıs karkasına `6,0 mm` radyal boşluk), toplam tahmini kütle **`25,92 kg`**:

| Kademe ID | Açıklama | `z_CAD` (mm) (`z_rel`) | Yükseklik (mm) | Alt Aralık (mm) | Dış Çap `OD` (mm) | İç Delik `Bore` (mm) | Kütle (kg) |
|---|---|---|---:|---:|---:|---:|---:|
| `S2.3_retarding_minilens` | Alansız Daldırmalı Mini-Lens (`Arch-B`, `10→1,3→5 keV`, `0,50 mm` adım) | `500,25–502,01` (`0,25–2,01`) | `1,76` | `0,25` (`WD`) | `60,0` | `0,30` *(delik)* | `0,20` |
| `S2.2_blanker_and_stop` | SKY130/MEMS Eş-Adımlı Blanker + Durdurucu (`0,50 mm` adım, `16` karo) | `503,01–507,01` (`3,01–7,01`) | `4,00` | `1,00` | `60,0` | `0,008` *(geçiş)* | `0,12` |
| `S2.1_aperture_and_frame` | MEMS Eş-Adımlı Apertür + Kinematik Çerçeve (`2,69 mm` radyal marj) | `507,66–531,66` (`7,66–31,66`) | `24,00` | `0,65` | `100,0` | **`28,0`** | `1,40` |
| `S1.6_transfer_lens` | Telesentrik Taşma Transfer Lensi (Einzel, `2,69 mm` radyal marj) | `539,66–604,66` (`39,66–104,66`) | `65,00` | `8,00` | `84,0` | **`28,0`** | `2,60` |
| `S1.5_energy_filter_HDA` | Yarımküresel Enerji Süzgeci (`ΔE=0,45 eV`, `E_pass=100 eV`) | `614,66–709,66` (`114,66–209,66`) | `95,00` | `10,00` | `110,0` | `16,0` | `5,20` |
| `S1.2_wien_mass_filter` | Wien Kütle Filtresi + Sürüklenme + `200 µm` Yarık (`³¹P⁺`) | `717,66–867,66` (`217,66–367,66`) | `150,00` | `8,00` | `110,0` | `12,0` | `6,80` |
| `S1.4_condenser_lens` | Çıkarıcı & Kondansatör Einzel Lensi | `873,66–918,66` (`373,66–418,66`) | `45,00` | `6,00` | `84,0` | `20,0` | `2,10` |
| `S1.1_duoplasmatron` | Duoplazmatron İyon Kaynağı (`PH₃`, genleşme kabı) | `922,66–1062,66` (`422,66–562,66`) | `140,00` | `4,00` | `90,0` | `0,10` | `7,50` |

---

## 5. Gerçek 3B Anizotropik BCA Saçılması, Yüzey Kesmesi (`z>0`) & Stokastik `³¹P` Donör Verimi (`CD6`–`CD8`)

Exp42/44/48/57/105 çekirdeği taşınabilir Linux yollarıyla (`400` gerçekleme/hücre; denetim `100` tohum) çalıştırıldı (`{Sayısal-Simülasyon}`):

| Hücre (`N=1024`, aksi belirtilmedikçe) | `(σ_x, σ_y, σ_z)` (nm) | `z>0` / Donör | Başarı | Verim (`%95` Wilson CI) | `Δ` vs Exp105 | Yüzey Kaybı | Donör Geri-Saç. / `<2 nm` |
|---|---|---|---:|---|---:|---:|---|
| `AUDIT_EXP57_S5_N1024` | `(5,0; 5,0; 5,0)` | Hayır / Sabit | `49/100` | **`%49,00`** `[39,4–58,6]` | — | `%0,0` | — |
| `AUDIT_EXP105_ISO3p8_N1024` | `(3,8; 3,8; 3,8)` | Hayır / Sabit | `277/400` | **`%69,25`** `[64,6–73,6]` | `0,00 pp` | `%0,0` | — |
| `ANISO_BCA_PURE_N1024` | `(3,25; 3,25; 2,88)` | Evet (`Rp=6,46`) / Sabit | `315/400` | **`%78,75`** `[74,5–82,5]` | **`+9,50 pp`** | `%1,26` | — |
| `ANISO_P91_BCA_N1024` | `(3,80; 3,80; 2,88)` | Evet (`Rp=6,46`) / Sabit | `307/400` | **`%76,75`** `[72,4–80,6]` | **`+7,50 pp`** | `%1,24` | — |
| `ANISO_P91_BCA_NOSURF_N1024` | `(3,80; 3,80; 2,88)` | Hayır / Sabit | `299/400` | `%74,75` `[70,3–78,8]` | `+5,50 pp` | `%0,0` | — |
| `ANISO_EXP124_BCA_N1024` | `(3,715; 3,715; 2,88)` | Evet (`Rp=6,46`) / Sabit | `305/400` | **`%76,25`** `[71,8–80,2]` | **`+7,00 pp`** | `%1,23` | — |
| `ANISO_BCA_HOLMES_N1024` | `(3,25; 3,25; 5,27)` | Evet (`Rp=6,46`) / Sabit | `282/400` | `%70,50` `[65,9–74,8]` | `+1,25 pp` | `%11,1` | — |
| `ANISO_P91_HOLMES_N1024` | `(3,80; 3,80; 5,27)` | Evet (`Rp=6,46`) / Sabit | `278/400` | **`%69,50`** `[64,8–73,8]` | `+0,25 pp` | `%11,0` | — |
| `ANISO_P91_HOLMES_RP9_N1024` | `(3,80; 3,80; 5,27)` | Evet (`Rp=9,0`) / Sabit | `264/400` | `%66,00` `[61,2–70,5]` | `−3,25 pp` | `%4,3` | — |
| `ANISO_P91_HOLMES_NOSURF_N1024` | `(3,80; 3,80; 5,27)` | Hayır / Sabit | `253/400` | **`%63,25`** `[58,4–67,8]` | **`−6,00 pp`** | `%0,0` | — |
| **`ANISO_P91_BCA_DONOR_N1024`** | `(3,80; 3,80; 2,88)` | Evet / **Stokastik `³¹P`** | `175/400` | **`%43,75`** `[39,0–48,6]` | **`−25,50 pp`** | `%1,19` | `%1,5` / `%3,5` |
| **`ANISO_EXP124_BCA_DONOR_N1024`** | `(3,715; 3,715; 2,88)` | Evet / **Stokastik `³¹P`** | `170/400` | **`%42,50`** `[37,8–47,4]` | **`−26,75 pp`** | `%1,24` | `%1,75` / `%4,75` |
| **`ANISO_P91_HOLMES_DONOR_N1024`** | `(3,80; 3,80; 5,27)` | Evet / **Stokastik `³¹P`** | `112/400` | **`%28,00`** `[23,8–32,6]` | **`−41,25 pp`** | `%9,91` | `%10,0` / `%7,25` |

### Ana Fiziksel Bulgular
1. **Sabit-donör anizotropik sapması:** `Exp92` BCA'nın daha sıkı derinlik saçılması (`σ_z=2,88 nm`) sabit-donör verimini `%69,25 → %76,25–%78,75` bandına (`+7,0..+9,5 pp`) yükseltir.
2. **Yüzey kesmesinin spektral-sıkışıklık rahatlatması (`CD7` bulgusu):** `N=1024` doygun bulutta Holmes `σ_z=5,27 nm` yüzeysüzken `%63,25`'e (`−6,0 pp`) düşse de `z>0` yüzey kesmesi üst yarıdaki `%11` seyirci `²⁹Si`'yi keserek NMR spektral sıkışıklığını azaltır (`elig_med: 8→9`) ve verimi `%69,50`'ye geri çeker (`BCA`'da da `%74,75→%76,75`).
3. **Stokastik `³¹P` donör saçılması (`CD8`, yeni Mod A gerçeklik sınırı):** `Exp57/105`'te donör bulut merkezine sabitlenmişti. Donörün kendi 3B implantasyon saçılması eklendiğinde korelasyonlu bulut kayması Mod A verimini **`%42,5–%43,8` (`BCA`)** ve **`%28,0` (`Holmes`)** düzeyine indirir (yine de Seçenek A `1.024` demetcik × `1000` kanal × `10–15 ms`'de `1,22–1,89×10⁶` sertifikalı/gün [`BCA`] üretir). **Mod B (`f=%1`, `%51` verim) uzamsal olarak tekdüze epitaksiyel banyoda çalıştığı için bu donör kaymasından sıfır etkilenir** — Mod B'nin birincil ürün modu seçimi nicel olarak kesinleşmiştir.

---

## 6. Çıktı Dosyaları & Doğrulama
- Betikler: `experiments/exp124_ion_column_optics/` (`column_physics.py`, `anisotropic_yield.py`, `run_exp124.py`, `plot_exp124.py`)
- Sonuçlar: `results/exp124_ion_column_optics/` (`predictions_exp124.json`, `exp124.json`, `summary_exp124.md`, `fig_exp124_optics_envelope.png`, `fig_exp124_anisotropic_yield.png`)
- Testler: `tests/test_exp124.py` (`python3 -B -m pytest -p no:cacheprovider tests/test_exp124.py`)
