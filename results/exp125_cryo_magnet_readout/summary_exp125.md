# Exp125 — Risk R7 (`1,50 T / ≤0,4 T` Aktif Karşı-Sargılı Kriyo-Mıknatıs + Nb Meissner Kalkan), 5-Kademe Kriyo/RF Kapanışı ve Risk R8 Faz-Duyarlı Vadi Girişimi

**Durum:** **CV1–CV6 6/6 PASS → BAŞARI (`success: true`)**. Tüm öngörüler hesaptan önce `predictions_exp125.json` dosyasında kayıt altına alınmıştır. **Laboratuvar ölçümü yoktur (`no_lab_measurement: true`)**; tüm sonuçlar `{Analitik}`, `{Sayısal-Simülasyon}`, `{Model}`, `{Literatür}` ve `{Varsayım}` etiketleriyle ayrıştırılmıştır.

---

## 1. Risk R7 Kapanışı: 8-Bobinli Aktif Karşı-Sargılı NbTi Mıknatıs + Nb Meissner Kalkan (`magnet_solver.py`)

### 1.1 Sayısal Doğrulama ve Yakınsama Kapıları `{Analitik}+{Sayısal-Simülasyon}`
- **Süperiletken Küre Analitik BEM Kıyaslaması (`n_rings = 160`, `R = 40 mm`, `B_0 = 0,10 T`):**
  - Yüzey akımı `K_phi` maksimum göreli hata: **`%0,181`** (`119.523` vs analitik `119.366 A/m`).
  - İç bölge kaçak alanı `max|B_in|/B_0`: **`1,36×10⁻³`**.
  - Dış ekvator (`r = 1,05 R`) göreli hata: **`4,10×10⁻⁴`**.
- **Maxwell Özdeşlikleri:** `max|∇·B|` göreli hata **`7,90×10⁻⁷`**; `max|B - ∇×A|` göreli hata **`8,77×10⁻⁷`**.
- **Kareleme ve BEM Yakınsaması:**
  - 2B Gauss-Legendre bobin karelemesi (`8×8` vs `12×12`): örnek merkezinde göreli fark **`4,54×10⁻¹⁴`** (`≪ 10⁻⁵`).
  - Nb kalkan BEM ağı (`M = 102` vs `M = 206` halka): örnek alanında göreli fark **`5,85×10⁻⁸`** (`≪ 10⁻⁵`); rezonatör kenarında `0,0216 → 0,0108 mT` (`Δ = 0,0108 mT`).
- **Manyetik Enerji Eşitliği:** Endüktans matrisi `½ Iᵀ L I = 18,941 kJ` vs doğrudan hacimsel integral `∫(|B|²/2μ₀) dV = 18,895 kJ` → göreli fark **`%0,244`** (`≤ %2,5`).
- **Newton 3. Yasa Eksenel Kuvvet Dengesi:** 8 bobinin toplam eksenel kuvvet artığı **`-0,276 kN`** (`176,3 kN` tepe kuvvetin `%0,16`'sı).

### 1.2 Elektromanyetik ve Süperiletken Mühendislik Sonuçları (`CV1–CV3 PASS`)
- **Örnek Aktif Alanı (`r ≤ 2,3 mm`, `3,2×3,2 mm` yonga, `|z| ≤ 0,5 mm`):**
  - Merkez alan: **`B_z(0,0) = 1,500000 T`**; maksimum göreli homojenlik sapması **`17,81 ppm`** (`1,78×10⁻⁵`, `< 100 ppm` şartından `5,6×` iyi); `max|B_r| = 0,011 mT`.
  - Nb kalkanın örnek merkezindeki geri-tepki alanı (`0,032 mT`) doğrudan doğrusal kuplaj matrisine dahil edilerek telafi edilmiştir.
- **NbTiN Rezonatör Sakin Bölgesi (`z_loc = -155,0 mm` / `z_makine = 345,0 mm`, `r ≤ 25 mm`, `Δz = ±3 mm`, alan `1.963,5 mm²` `≫ 8,43 mm²` Exp109 ayak izi):**
  - **Kalkansız (yalnız aktif karşı-sargı):** `max|B| = 3,08 mT` (`0,00308 T`, `≤ 0,25 T` hedefinin `81×` altı; `|B_z| ≤ 2,86 mT`, `|B_r| ≤ 1,92 mT`).
  - **Nb Meissner Kalkanlı (`Ø16 mm` koaks bacalı açık-port kap):** **`max|B| = 0,0223 mT` (`22,3 µT`)** — **`|B_z| ≤ 0,0216 mT`** ve **`|B_r| ≤ 0,0078 mT`** (**yatay veya dikey her iki yonga yöneliminde de `|B_perp| ≤ 10 mT` sınırının `>450×` altında!**, ek zayıflatma `138,3×`).
- **Nb Kalkan Meissner Bütünlüğü ve Cryoperm-10 Dış Kılıf:**
  - Kap dışındaki kalkansız alan `≤ 19,71 mT`; demanyetizasyon dahil gerçek taranmış yüzey alanı `max(μ₀|K_phi|) = 117,12 mT < B_c1(Nb, 4,2 K) = 134,95 mT` (`1,0 K`'de `168,0 mT`, `20 mK`'de `170,0 mT`) → **4,2 K'da dahi vortekssiz Meissner rejimi (`meissner_vortex_free_4p2K = true`)**.
  - `Cryoperm-10` dış silindir (`R = 39–41 mm`, `2 mm` et kalınlığı, `μ_r(4K) ≈ 20.000`, `B_sat = 0,75 T`): doyum marjı **`38,1×`**, analitik enine kalkan faktörü `488,8×` (koruyucu ek marj olarak Nb BEM hesabına katılmamıştır).
  - Üst iyon kolonu referans düzleminde (`z_loc = +268,0 mm`, `z_makine = 768,0 mm`) kaçak alan: **`108,1 mT`** (eksenel `B_z` olduğundan paraksiyal ışın sapması doğurmaz, yalnızca hafif Larmor dönüşü üretir).
- **NbTi Kritik Akım (Bottura 2000, `Cu:SC = 2:1`, doluluk `%70`), Gerilme ve Quench:**
  - En yüksek çalışma oranı: **`I/I_c(4,2 K) = 0,212`** (`≤ 0,55`, `M_lower`); en düşük sıcaklık marjı **`ΔT = 2,55 K`**.
  - En yüksek Lorentz çember gerilmesi: **`|σ_hoop| = 52,7 MPa`** (`≤ 80 MPa`, `S_upper`); toplam NbTi tel uzunluğu **`5,48 km`**.
  - Pasif boşaltma direnci quench koruması (`R_dump = 1,563 Ω`, `V_max = 400 V`, `τ = 0,370 s`, `t_detect = 30 ms`, Cu RRR=100 MIITs): **`T_hotspot = 64,6 K`** (`≤ 150 K`).

### 1.3 CAD v3.0 İçin Kesin Bobin ve Kalkan Geometrisi (mm) `{Model}`
Referans (`CAD v3.0`, `research/atom_lithography_machine/cad/params.py`): `z_loc = 0,0 mm` örnek yonga yüzeyi ↔ **`Z_WAFER = 500,0 mm`**. Mıknatıs temiz iç delik çapı **`Ø 150,0 mm` (`R_bore = 75,0 mm`)**, orta düzlem optik/yonga erişim aralığı **`36,0 mm` (`z_loc ∈ [-18,0; +18,0] mm`, `z_makine ∈ [482,0; 518,0] mm`)**, dış karkas çapı **`Ø 352,0 mm` (`R_dış = 176,0 mm`)**, `s = 0,5` UHV vakum odası iç yarıçapı **`R_iç = 182,0 mm`** (radyal vakum boşluğu = **`6,0 mm`**), bobin yığını eksenel aralığı **`z_makine ∈ [316,0; 612,0] mm`** (`z ∈ [285,0; 620,0] mm` oda içinde alt tabana `31,0 mm`, üst kapağa `8,0 mm` boşluk).

| Bileşen | Rol / Malzeme | `R_in` (mm) | `R_out` (mm) | `z_loc` (mm) | `z_makine` (mm) | Sarım `N` | Akım `I` (A) | `B_peak` (T) | `I/I_c` | `σ_hoop` (MPa) | `F_z` (kN) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `M_upper` | Ana üst (NbTi) | 78,0 | 112,0 | +18,0 .. +72,0 | 518,0 .. 572,0 | 1600 | +40,24 | 2,07 | 0,026 | +5,0 | +22,86 |
| `M_lower` | Ana alt (NbTi) | 78,0 | 112,0 | -72,0 .. -18,0 | 428,0 .. 482,0 | 1600 | +216,47 | 3,74 | 0,212 | +42,0 | +176,27 |
| `S_upper` | Homojenlik üst | 78,0 | 116,0 | +76,0 .. +112,0 | 576,0 .. 612,0 | 1100 | +255,91 | 3,13 | 0,199 | -52,7 | -27,14 |
| `S_lower` | Homojenlik alt | 78,0 | 116,0 | -112,0 .. -76,0 | 388,0 .. 424,0 | 1100 | -195,26 | 3,75 | 0,177 | +22,4 | -141,71 |
| `A_upper` | Aktif kalkan üst | 144,0 | 168,0 | +20,0 .. +104,0 | 520,0 .. 604,0 | 960 | -167,99 | 1,88 | 0,055 | +21,9 | -14,99 |
| `A_lower` | Aktif kalkan alt | 144,0 | 168,0 | -104,0 .. -20,0 | 396,0 .. 480,0 | 960 | -57,20 | 1,05 | 0,014 | +4,1 | -11,04 |
| `B_upper` | Karşı-sargı üst | 56,0 | 82,0 | -145,0 .. -121,0 | 355,0 .. 379,0 | 400 | +83,90 | 1,28 | 0,030 | -4,1 | -4,47 |
| `B_lower` | Karşı-sargı alt | 56,0 | 82,0 | -184,0 .. -160,0 | 316,0 .. 340,0 | 400 | +22,48 | 0,31 | 0,004 | -0,3 | -0,06 |
| **Nb Kap** | `Nb RRR>300` (`2,5 mm`, `r_fillet=4 mm`) | 32,0 | 34,5 | -174,0 .. -136,0 | 326,0 .. 364,0 | — | Baca: `r=8 mm`, `h=11 mm` (`z_loc=-125 / z_makine=375`) | `117,1 mT` | `<B_c1` | — | — |
| **Cryoperm** | `Cryoperm-10` (`2,0 mm`) | 39,0 | 41,0 | -180,0 .. -124,0 | 320,0 .. 376,0 | — | Dış kılıf (`h=56 mm`) | `19,7 mT` | `38× < B_sat` | — | — |
| **Rezonatör** | `NbTiN` taşıyıcı disk | 0,0 | 25,0 | -155,0 ± 3,0 | 345,0 ± 3,0 | — | Alan `1963,5 mm²` | `0,022 mT` | `≤0,4 T` | — | — |

---

## 2. Birleşik 5-Kademe Kriyo Termal Bütçe, RF SNR ve Üretim Hızı (`cryo_rf_solver.py`, `CV4–CV5 PASS`)

- **Tekrarlanabilirlik Kapısı:** Exp110 (`NL=58`, 156 hat → MXC `5,2376 µW`, 4K `1,482 W @7,5 mW`) ve Exp112 (`NL=163`, 56 hat → 4K `0,2296 / 0,5488 W`) okuma yükleri `<10⁻¹²` farkla birebir doğrulandı.
- **Sistem Yükleri Dahil 5-Kademe Bütçe (9000 kanal, `-100 dBm/ton`, kalıcı-mod mıknatıs uçları + 4K kriyo-CMOS + radyasyon/dikme yükleri [`50K: 2,5 W`, `4K: 95 mW`, `Still: 0,80 mW`, `CP: 15 µW`, `MXC: 2,0 µW`] eklenmiş `{Literatür}+{Model}+{Varsayım}`):**

| Mod & Nokta | Hat | `50 K` (`<40 W`) | `4 K` (`<1,0 W PT410`) | `Still` (`<40 mW`) | `CP` (`<200 µW`) | `MXC/1K` (`<19 µW / <100 mW`) | Tek PT410? |
|---|---:|---:|---:|---:|---:|---:|---|
| `20 mK` Baz, `NL=163`, `2,1 mW` HEMT | 56 | 7,54 W (%19) | **0,325 W** (%33) | 1,14 mW (%2,9) | 54,5 µW (%27) | **3,94 µW** (%21) | **PASS** |
| `20 mK` Baz, `NL=160`, `7,8 mW` HEMT | 57 | 7,63 W (%19) | **0,654 W** (%65) | 1,15 mW (%2,9) | 55,1 µW (%28) | **3,97 µW** (%21) | **PASS** |
| `20 mK` Baz, `NL=160`, `10,5 mW` HEMT | 57 | 7,63 W (%19) | **0,808 W** (%81) | 1,15 mW (%2,9) | 55,1 µW (%28) | **3,97 µW** (%21) | **PASS** |
| `20 mK` Baz, `NL=110`, `7,8 mW` HEMT | 82 | 9,88 W (%25) | **0,899 W** (%90) | 1,30 mW (%3,2) | 72,4 µW (%36) | **4,80 µW** (%25) | **PASS** |
| `20 mK` Baz, `NL=110`, `10,5 mW` HEMT | 82 | 9,88 W (%25) | **1,121 W** (%112) | 1,30 mW (%3,2) | 72,4 µW (%36) | **4,80 µW** (%25) | PT415/420 gerekir |
| `1 K` Alternatif, `NL=160`, `7,8 mW` | 57 | 7,63 W (%19) | **0,654 W** (%65) | — | — | **11,84 mW** (%12) | **PASS** |
| Ürün Ölçeği (34 kanal), `20 mK`, `7,8 mW` | 1 | 2,59 W (%6,5) | 0,105 W (%10,5) | 0,81 mW (%2,0) | 15,7 µW (%7,8) | 2,03 µW (%10,7) | **PASS** |

- **Dispersif RF SNR Marjı (`-100 dBm/ton`, `Ql=1000`, `1,5 dB` hat kaybı, `|ΔΓ|=0,05`):**
  - `20 mK` + Rebelo `1,4 K` LNA (`T_sys = 2,01 K`): `SNR = 10` entegrasyon süresi **`0,0627 ms`** (`200` noktalı tarama **`12,5 ms` `≪ t_eff = 1445 ms`**).
  - `1,5 K` + `3,0 K` LNA (`T_sys = 5,75 K`): `SNR = 10` süresi **`0,179 ms`** (`200` nokta **`35,9 ms`**, zayıf `|ΔΓ|=0,01` senaryosunda dahi `4,49 ms ≤ 10 ms`). Okuma `-100 dBm/ton` sınırında RF-foton darboğazında değildir.

---

## 3. Risk R8 Analizi: Faz-Duyarlı Silikon Vadi Girişimi & Dar `t_c` Penceresi (`ancilla_valley_r8.py`, `CV6 PASS`)

- **Exp118 Tekrarlama Kapısı:** `R20_G100` (`1,0000`) ve `R15_G1` (`0,5349 → 0,7732`) birebir doğrulandı.
- **Fiziksel Model (200.000 MC, ayrık Si elmas kafesi `a_Si = 0,5431 nm`, `k_0 = 9,834 nm⁻¹`, `R_0 = 20 nm`, `t_c,ref = 1 GHz`):**
  - **V1 (Arayüz 2-vadi):** `|cos(k_0 z + φ_0)|` (MOS/arayüz yardımcı noktası).
  - **V2 (Koiller-Hu-Das Sarma 6-vadi):** `|cos(k_0 x) + cos(k_0 y) + cos(k_0 z)| / 3` (silikon hacim donor-nokta).
- **Verim, Aşırı Örnekleme `N_99` ve Üretim Hızı (Mod B `f=%1`, 9000 kanal, `%50` çevrim):**

| Senaryo (`R_0=20 nm, λ=2,0 nm`) | Vadi Yok | `V1` (2-vadi) | `V2` (Koiller 6-vadi) | `N_99` (`V2`) | Mod B Sertifikalı Yazmaç/Gün (`V2`) |
|---|---:|---:|---:|---:|---:|
| **Baz `20 mK` (`S6.8=D`, `t_eff=1,445 s`)** | `1,000` | — | — | 1 | **`1,372×10⁸`** (referans `1,00×`) |
| `1 K` + `W4` (`1 MHz–10 GHz`, `G=100×`, Exp118) | `1,0000` | `1,0000` | **`1,0000`** | 1 | `4,336×10⁷` (`3,17×` yavaş) |
| `1 K` + `W2` (`100 MHz–10 GHz`, `G=10×`, gerçekçi) | `0,9953` | **`0,9694`** | **`0,9322`** (`λ=1,5 nm: 0,8781`) | 2 (3) | **`4,042×10⁷`** (`3,40×` yavaş) |
| `1 K` + `W1` (`316 MHz–3,16 GHz`, `G=3×`, dar) | `0,8310` | `0,7367` | **`0,6096`** (`λ=1,5 nm: 0,5405`) | 5 (6) | `2,643×10⁷` (`5,19×` yavaş) |
| `1 K` + `W1` (`316 MHz–3,16 GHz`, `G=1×`, ayarsız) | `0,5189` | `0,4370` | **`0,3354`** | 12 | `1,454×10⁷` (`9,44×` yavaş) |

- **Maliyet Başa-Baş Sınırı (`S6.8=C` vs Baz `S6.8=D` DR, `NL=163`, merkez zincir `16,875`):**
  - Altın maliyet başa-başı (`+900` birim DR farkını ek zincirlerin yuttuğu sınır): **`p_crit_cost = 0,5122`**.
  - Altın oran eşitliği (`0,5215` DR bazına ulaşma sınırı): **`p_crit_frac = 0,4812`**.
  - **Hüküm:** Gerçekçi `≥2` onluk `t_c` penceresi ve `G ≥ 10×` kapı ayarı sağlandığı sürece, gerçek faz-duyarlı 6-vadi sıfırları altında bile `p ≥ 0,878–0,932 ≫ p_crit = 0,512` kalır ve `1 K` alternatifi maliyet avantajını (`altın oran ≈ 0,453`) korur. Yalnızca kapı ayarı `G ≤ 1–3×` seviyesine çökerse ve pencere `≤1` onluğa daralırsa `p` başa-baş sınırının altına iner. `1 K` kolunun nihai kapısı yine implante donorlarda `1–1,5 K` ESR/ENDOR laboratuvar gösterimidir; baz tasarım Exp121 kararıyla **`S6.8=D` (`20 mK`)** olarak sağlamdır.

Dosyalar: `predictions_exp125.json`, `exp125.json`, `plot_data_exp125.json`, `fig_exp125_bfield_map.png`, `fig_exp125_thermal_snr.png`; betikler `experiments/exp125_cryo_magnet_readout/{magnet_solver,cryo_rf_solver,ancilla_valley_r8,run_exp125,plot_exp125}.py`; testler `tests/test_exp125.py`.
