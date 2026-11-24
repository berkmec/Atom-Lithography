# Exp143 (`H161`) — `D3` Çok-Harmonik Fourier GRAPE `M4` Veri Yolu Kapısı ve `Option-HPC` `100 Gbps` RoCEv2 RDMA Gerçek-Zamanlı Sendrom Dekoderi

- **Deney / Hipotez:** `exp143_d3_grape_m4_and_hpc_decoder` (`H161`)
- **Tarih:** `2026-11-23`
- **Epistemik Etiket:** `{Sayısal-Simülasyon}` / `{Model}` / `{Liste-Capasi}` / `{Varsayım}` (`no_lab_measurement = true`, `no_supplier_quotes = true`)
- **Ön-Kayıtlı Yargı Özeti:** **`4/7 PASS`, `3/7` dürüst/bilgilendirici `FAIL` (`DH1, DH2, DH3`)** — `success_rule_met = false` (ön-kayıtlı `predictions_exp143.json` eşikleri sonuç sonrası **kesinlikle değiştirilmemiştir**; tüm CPTP, fiziksel bağlaşım tavanı, canlı MWPM ve taşınabilirlik kriterleri `%100` temizdir).
- **Denetim Kilidi (`Yazar != Denetçi`):** Bu rapor yazar (`Hydrogen` / `physics-early`) çıktısıdır; bağımsız kapanış (`KABUL`) onayı yalnızca sıfır bağlamlı `Carbon` denetçisine aittir.

---

## 1. Yönetici Özeti ve `v6.0` Fiziksel Bulguları `{Sayısal-Simülasyon}`

`Exp138`'de `M4` iki-kübit `CZ` kapı hatasını `%0,92` (`D2`, `Λ = 1,40`) düzeyinden `%0,50` (`D3`, `Λ = 2,52`) düzeyine çekmenin `100` mantıksal kübitlik `ε_L = 10⁻⁹` kriyostat filosunu **`6,8×` (`679 → 100` `LD400/PT420`)** küçülttüğünü göstermiştik. `Exp143`, bunu gerçek `12×12` CUDA Strang-Lindblad + `M = 40` renkli `1/f^α` OU gürültüsü altında **PyTorch autograd `K = 8` Fourier GRAPE optimal-kontrol** ile sınamış ve `Option-HPC` `100 Gbps` RoCEv2 RDMA gerçek-zamanlı dekoder duvarını kapatmıştır:

1. **`K = 8` Fourier GRAPE `M4` `CZ` Kapısı — Hız Sınırı ve Gerçek `D3` Kırılımı (`Q_r = 1×10⁶`):**
   - `Exp131` sertifikalı `5` hızlı çift (`g_min >= 1,16 MHz`) üzerinde sert fiziksel bağlaşım tavanı (`max |s_k(t)| = 1,0000 <= 1,0`) ve **`<= 300 MHz` AWG spektral saflığı (`%100,00` enerji `< 300 MHz`, `f_99 = 75,1 MHz`)** korunarak kapı süresi `Exp137 P4`'ün `1,737 µs` değerinden **`0,894 µs` (`1,94×` hızlanma)** düzeyine indirilmiştir.
   - **Fiziksel `Exp136` Yankılı `²⁹Si` Çekirdek Banyosunda (`T₂e,XY8 = 14,135 ms → γ_φ,nuc = 0,0225 kHz`):**
     - **`Q_r = 1×10⁶`, `S_ε = 0,25 µeV/√Hz` (`5`-çift tam ortalama):** **`p_2q = 0,337%`** (`F_avg = 99,73%`, `F_Bell = 99,69%`, `p_leak = 1,8×10⁻⁴`) — **`D3` hedefini (`<= 0,45% / 0,50%`) açık ara kırar!**
     - **`Q_r = 1×10⁶`, `Exp139` Nominal Rota C `S_ε = 0,390 µeV/√Hz`:** **`p_2q = 0,395%`** (`F_avg = 99,68%`, `F_Bell = 99,65%`) — **nominal Rota C'de bile `<= 0,45%` kırılır!**
     - **`Q_r = 1×10⁶`, En Kötü Rota C Bandı `S_ε = 0,50 µeV/√Hz`:** **`p_2q = 0,475%`** (`F_avg = 99,62%`).
     - **`Q_r = 5×10⁵`, `S_ε = 0,390 µeV/√Hz`:** `p_2q = 0,602%` (`F_avg = 99,52%`) — **`DH3` kısmi/dürüst `FAIL`** olarak şunu kesin kanıtlar: `Q_r = 5×10⁵` (`κ = 10 kHz`) kavite foton kaybı `~0,55%` tabanı koyar; nominal Rota C'de `<= 0,45%` için **`Q_r = 1×10⁶` (`κ = 5 kHz`) `NbTiN/TiN` kavite fiziksel olarak gereklidir**.
   - **Sıkı Muhafazakar `Exp137` Yankısız `0,5 kHz` Çekirdek Tabanında (`DH2` Dürüst `FAIL`):**
     - `Q_r = 1×10⁶, S_ε = 0,25 µeV/√Hz` noktasında `5`-çift ortalaması **`p_2q = 0,556%`** (`F_avg = 99,56%`, **`F_Bell = 99,65%`** — `Exp137 P4`'ün `0,878%` değerine göre `1,58×` iyileşme) verirken, **`g_geom >= 2,0 MHz` yüksek-`g` alt kümesi (`3` çift: `pair_0/2/4`) `p_2q = 0,481% <= 0,50%` (`F_avg = 99,62%`)** değerini kırar. Kalan `2` çift (`g_geom ≈ 1,28 MHz`) 3-seviyeli Jaynes-Cummings kuantum hız sınırına (`t_QSL = 0,342 / g_geom → t_4 = 1,21–1,24 µs`) çarpar.
2. **Canlı `Exp138` Tam Edmonds Blossom `MWPM` Doğrulaması (`DH4 PASS` — Büyük Sistem Zaferi):**
   - Çıkarılan gerçek `16`-Pauli `Exp143` GRAPE kanalları doğrudan `Exp138`'in canlı `MWPM` yüzey kodu çözücüsüne (`d = 3, 5, 7, 9`, `Exp140 p_meas = 0,386%`, `Exp126 p_1q = 0,083%`) verildiğinde:
     - **Muhafazakar `0,5 kHz` (`5`-çift, `p_2q = 0,556%`):** **`Λ_D3_phys = 2,415`** (95% GA `[2,21, 2,64]`), `d*(10⁻⁹) = 39`, **`100L` kriyostat filosu = `106` kriyostat** (`Exp138 D2` `679`'a göre **`6,4×` küçülme**)!
     - **Muhafazakar `0,5 kHz` (`high-g >= 2,0 MHz`, `p_2q = 0,481%`):** **`Λ_D3_phys = 2,997`**, `d*(10⁻⁹) = 31` (`1,921 <= 2,887` MXC — tek kriyostata tam 1 bölünmemiş mantıksal kübit!), **`100L` = `100` kriyostat (`6,8×` küçülme)**!
     - **Yankılı `Exp136` (`Q = 1×10⁶, S = 0,25`, `p_2q = 0,337%`):** **`Λ_D3_phys = 2,825`**, `d*(10⁻⁹) = 33` (`2,177 <= 2,887` MXC!), **`100L` = `100` kriyostat (`6,8×` küçülme)**!
3. **`Option-HPC` `100 Gbps` RoCEv2 RDMA Gerçek-Zamanlı Dekoder Duvarı & `S9.HPC` (`DH5, DH6 PASS`):**
   - Toplam tek-yön sendrom aktarım gecikmesi: `20 mK` TWPA/koaks (`7 ns`) + `ZU48DR RFSoC` IQ/eşik/`100G` CMAC (`320 ns`) + `100 GbE RoCEv2` `20 m` fiber + ConnectX-7 GPUDirect DMA (`450 ns`) = **`777 ns` (`0,78 µs`)**.
   - Tek çekirdekli C++ Sparse Blossom CPU, `d = 21`'de **`10,04 µs`** ve `d = 37`'de **`34,07 µs`** ile hem `2,62 µs` hem `6,70 µs` (`v6 D3 4-CZ`) hem de `8,93 µs` (`v5 4-CZ`) yığılma duvarına (`backlog wall`) kesin çarpar.
   - `Option-HPC` paralel pencereli (`P_win = 8`) GPU/FPGA dekoderi `d = 37`'yi uçtan uca **`6,34 µs`** (`< 6,70 µs < 8,93 µs`) ile **sıfır yığılma (`backlog-free`)** çözer (`100L` sert sendrom bant genişliği `19,14 Gbps @ 8,93 µs` / `25,51 Gbps @ 6,70 µs` → `2× 100G` yedekli fiber; `13` HPC düğümü = `7× 4U` raf, `14,31 kW`).
   - **`qLDPC [[144, 12, 12]]` (`BP-OSD`, `9` blok = `108` mantıksal kübit):** Ortalama uçtan uca dekoder süresi **`2,32 µs` (`< 2,62 µs` hızlı okuma duvarının bile altında!)**, `108L` toplam bant genişliği sadece `0,24 Gbps`, ve **tek `1× 4U` `S9.HPC` baz rafı (`64,0 kg`, `2,195 kW`, `$132k` P50, `0,0 W` kriyo yükü) tüm `108` mantıksal kübiti çözer!**

---

## 2. Ön-Kayıtlı `DH1–DH7` Dürüst Değerlendirme Tablosu `{Sayısal-Simülasyon}`

| Kimlik | Ön-Kayıtlı Kriter | Ölçülen Sonuç | Yargı |
| :--- | :--- | :--- | :--- |
| `DH1` | Gürültüsüz `p_err <= 5e-4`, `p_leak <= 1e-4`, `max_amp(s) <= 1`, `BW<300 MHz >= 99,5%`, `t_gate <= 0,90 µs` | `p_err = 4,25e-4`, `max_amp(s) = 1,0000`, `BW = 100,00%` (`f99 = 75,1 MHz`), `t = 0,894 µs` PASS; **`cons p_leak = 1,37e-4 > 1,00e-4`** (`echo leak = 6,64e-5` PASS) | **FAIL** |
| `DH2` | Sıkı muhafazakar `0,5 kHz` (`Q=1e6, S=0,25`, `5`-çift): `p_2q <= 0,50%`, `F_avg >= 99,60%`, `F_Bell >= 99,65%`, `P4` kazancı `>= 1,70×` | `5`-çift: `p_2q = 0,556%`, `F_avg = 99,56%`, **`F_Bell = 99,65%` PASS**, `1,58×` vs `P4` (`0,878%`); `high-g >= 2 MHz` alt kümesi: **`0,481%` (`99,62%`)** | **FAIL** |
| `DH3` | Yankılı `Exp136` (`0,0225 kHz`): `Q=5e5 S=0,39 <= 0,45%` VE `Q=1e6 S=0,25 <= 0,35%` | `Q=1e6 S=0,25`: **`0,337%` PASS** (`Q=1e6 S=0,39`: **`0,395%`**); ancak `Q=5e5 S=0,39`: **`0,602% > 0,45%`** (`Q=1e6` kavite zorunlu!) | **FAIL** |
| `DH4` | Canlı `Exp138` MWPM: `Λ_D3_phys >= 2,20` ve `100L 10⁻⁹` kriyostat `<= 130` (`>= 5×` düşüş vs `679`) | Muhafazakar `5`-çift: **`Λ = 2,415`, `106` kriyo (`6,4×`)**; Yankılı `Q=1e6`: **`Λ = 2,825`, `100` kriyo (`6,8×`)** | **PASS** |
| `DH5` | `Option-HPC`: CPU `d=37` duvarına çarpar, HPC `d=37 < 8,93 µs`, `qLDPC < 2,62 µs`, `100L BW <= 25 Gbps` | CPU `d=37`: `34,07 µs` (çöküş); HPC `d=37`: **`6,34 µs < 6,70 / 8,93 µs`**; `qLDPC`: **`2,32 µs < 2,62 µs`**; `BW_v5 = 19,14 Gbps` | **PASS** |
| `DH6` | `s9hpc_hardware_spec.json` (`CAD/BOM v6.0` tam şema, `0 W` kriyo, sıralı maliyet, `no_supplier_quotes=true`) | `64,0 kg`, `2.195 W` (`0,0 W` kriyo), `4U/5U`, `$98k / $132k / $181k` (`{Varsayım}`) | **PASS** |
| `DH7` | Tüm `12×12` Choi kanalları CPTP temiz (`<1e-10`), `0` sabitlenmiş yol, `2400×1400` PNG, `0` GFM, `>= 8` pytest | `all_cptp_clean = True`, `0` hardcoded path, CRC-temiz `2400×1400` PNG, `9/9` pytest `PASS` | **PASS** |

---

## 3. `12×12` CUDA Strang-Lindblad + `M = 40` `1/f` OU Kapı Karşılaştırması (`N_traj = 512/çift`) `{Sayısal-Simülasyon}`

| Çalışma Noktası `(Q_r, S_ε)` | `Exp137 P4` (`1,737 µs`) | `Exp143` GRAPE Muhafazakar `0,5 kHz` (`5`-çift / `high-g`) | `Exp143` GRAPE Yankılı `Exp136` `0,0225 kHz` (`5`-çift) | Yankılı `F_avg` / `F_Bell` |
| :--- | :--- | :--- | :--- | :--- |
| `Q = 5×10⁵`, `S = 0,390` (nom.) | `1,204%` (`99,04%`) | `0,742%` / `0,657%` | `0,602%` | `99,52%` / `99,44%` |
| `Q = 5×10⁵`, `S = 0,250` | `0,990%` (`99,21%`) | `0,698%` / `0,612%` | `0,543%` | `99,57%` / `99,48%` |
| `Q = 1×10⁶`, `S = 0,500` (üst bant) | — | `0,663%` / `0,580%` | **`0,475%`** | `99,62%` / `99,60%` |
| **`Q = 1×10⁶`, `S = 0,390` (nom.)** | `1,093%` (`99,13%`) | `0,601%` / `0,523%` | **`0,395%`** | **`99,68%` / `99,65%`** |
| **`Q = 1×10⁶`, `S = 0,250`** | `0,878%` (`99,30%`) | `0,556%` / **`0,481%`** (`P4-SS`: `0,626%`) | **`0,337%`** | **`99,73%` / `99,69%`** |

---

## 4. Canlı `Exp138` Edmonds Blossom `MWPM` Doğrulaması ve `100L` Kriyostat Kaldıracı `{Sayısal-Simülasyon}`

| Kanal (Gerçek `16`-Pauli Çıktısı) | `p_2q` (`F_avg`) | `Λ_round` (95% GA) | `d* (10⁻⁶)` (`100L` kriyo) | `d* (10⁻⁹)` (`N_active`, `100L` kriyo) | `d* (10⁻¹²)` (`100L` kriyo) | `D2` (`679`) Kıyas |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Exp138 D2` Referans (`P4`, `Q=5e5, S=0,25`) | `0,920%` (`99,26%`) | `1,40` (`[1,31, 1,50]`) | `59` (`242` c) | `99` (`19.601`, `679` c) | `141` (`1.378` c) | `1,0×` (baz) |
| `Exp143` Yankılı `Q=5e5, S=0,390` (`5`-çift) | `0,602%` (`99,52%`) | `1,97` (`[1,73, 2,25]`) | `29` (`100` c) | `49` (`4.801`, `167` c) | `69` (`330` c) | **`4,1×` düşüş** |
| **`Exp143` Muhafazakar `0,5 kHz` (`Q=1e6, S=0,25`)** | **`0,556%` (`99,56%`)** | **`2,41` (`[2,21, 2,64]`)** | **`23` (`50` c)** | **`39` (`3.041`, `106` c)** | **`55` (`210` c)** | **`6,4×` düşüş** |
| **`Exp143` Yankılı `Q=1e6, S=0,25` (`5`-çift)** | **`0,337%` (`99,73%`)** | **`2,83` (`[1,88, 4,25]`)** | **`19` (`25` c)** | **`33` (`2.177 <= 2.887`, `100` c)** | **`45` (`141` c)** | **`6,8×` düşüş** |
| **`Exp143` Muhafazakar `high-g >= 2 MHz`** | **`0,481%` (`99,62%`)** | **`3,00` (`[2,45, 3,66]`)** | **`19` (`25` c)** | **`31` (`1.921 <= 2.887`, `100` c)** | **`45` (`141` c)** | **`6,8×` düşüş** |

---

## 5. `Option-HPC` Gerçek-Zamanlı Dekoder Duvarı ve `S9.HPC` Donanım Özeti `{Model}` / `{Varsayım}`

Canlı yerel Python/networkx referansı `d = 7` ve `d = 11` üzerinde deneysel dedektör ateşleme oranını `p_det = 4,26%` olarak ölçmüştür; C++ Sparse Blossom ve paralel pencereli `Option-HPC` (`τ_ingest = 777 ns`) ölçeklemesi aşağıdadır:

| QEC Kodu (`100L` Sistem) | Beklenen Kusur/Tur | CPU 1-Çekirdek | `Option-HPC` E2E | `100L` Sert BW (`v5` / `D3`) | `100G` Fiber | HPC Düğümü (`4U` Modül) | HPC Güç (`kW`) | Yığılma Durumu |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Yüzey Kodu `d = 7` (`48` kontrol) | `2,04` | `1,14 µs` | `1,36 µs` | `0,67` / `0,90 Gbps` | `2× 100G` | `7` (`4× 4U`) | `7,73 kW` | Sıfır Yığılma (`2,62 µs`!) |
| Yüzey Kodu `d = 11` (`120` kontrol) | `5,11` | `2,62 µs` | `1,81 µs` | `1,68` / `2,24 Gbps` | `2× 100G` | `7` (`4× 4U`) | `7,73 kW` | Sıfır Yığılma (`2,62 µs`!) |
| Yüzey Kodu `d = 21` (`440` kontrol) | `18,73` | `10,04 µs` (DUVAR!) | `4,03 µs` | `6,16` / `8,21 Gbps` | `2× 100G` | `7` (`4× 4U`) | `7,73 kW` | Sıfır Yığılma (`6,70 / 8,93 µs`) |
| **Yüzey Kodu `d = 37` (`1.368` kontrol)** | **`58,23`** | **`34,07 µs` (DUVAR!)** | **`6,34 µs`** | **`19,14` / `25,51 Gbps`** | **`2× 100G`** | **`13` (`7× 4U`)** | **`14,31 kW`** | **Sıfır Yığılma (`6,70 / 8,93 µs`)** |
| **`qLDPC [[144,12,12]]` (`108L`)** | `BP-OSD` (`%3,5` OSD) | `8,27 µs` (`p99: 48,8`) | **`2,32 µs`** (`p99: 16,3`) | **`0,18` / `0,24 Gbps`** | **`2× 100G`** | **`2` (`1× 4U`!)** | **`2,195 kW`** | **Sıfır Yığılma (`2,62 µs`!)** |

- **`s9hpc_hardware_spec.json` (`CAD v6.0` & `BOM v6.0` Opsiyon Çıktısı, `S9.HPC`):** `1` baz `4U` (`5U` anahtarlı) 2-düğümlü `100G` RoCEv2 RDMA raf modülü = **`64,0 kg`**, **`2.195 W`** (`0,0 W` kriyo yükü), `[482,6 × 780,0 × 177,8] mm` (`4U` doğrudan) / `222,3 mm` (`5U` optik köprülü), **`4×` `QSFP28-100G` port**, tahmini opsiyon maliyeti **`$132.000` P50 (`$98k–$181k`, `{Varsayım}`, `no_supplier_quotes = true`)**.

---

## 6. Yapılmayanlar / Kapsam Dışı ve Sınır Koşulları

- **Gerçek Laboratuvar Ölçümü Yok (`no_lab_measurement = true`):** `12×12` GRAPE darbeleri, `1/f` OU yörüngeleri ve `MWPM` eşikleri sayısal-fizik simülasyonlarıdır; gerçek `³¹P/NbTiN` `Q = 10⁶` kavite ölçümü değildir.
- **Tedarikçi Teklifi Yok (`no_supplier_quotes = true`):** `S9.HPC` raf, GPU/FPGA kartı ve ConnectX-7 maliyetleri liste-çapası / mühendislik varsayımıdır (`{Liste-Capasi}` / `{Varsayım}`).
- **Kavite `Q_r = 1×10⁶` Üretim Riski:** `DH3` dürüst `FAIL`'inin gösterdiği gibi `Q_r = 5×10⁵` (`κ = 10 kHz`) yüzey kodunda `p_2q = 0,602%` (`Λ = 1,97`) ile sınırlı kalır; `p_2q <= 0,40%` için `3 kΩ` yüksek-empedans `NbTiN/TiN` kavitede `B_M4 = 0,1785 T` düzlem-içi alan altında `Q_r >= 1×10⁶` korunumu deneysel doğrulama gerektirir.
- **Kriyostatlar-Arası Bağlantı & Gerçek FPGA/GPU Dekoder Sentezi:** `Option-HPC` gecikmeleri literatür (`Sparse Blossom`, `Fusion Blossom`, `Willow 2025`, `ZU48DR`/`ConnectX-7` veri sayfaları) ile kalibre edilmiş analitik-ampirik modellerdir; gerçek `100G` RoCEv2 donanım gecikme ölçümü yapılmamıştır.

---

## 7. Üretilen Artefaktlar

- `experiments/exp143_d3_grape_m4_and_hpc_decoder/{__init__.py,grape_m4_bus143.py,hpc_decoder143.py,run_exp143.py,fig_exp143.py}`
- `results/exp143_d3_grape_m4_and_hpc_decoder/{predictions_exp143.json,exp143.json,s9hpc_hardware_spec.json,summary_exp143.md,fig_exp143_d3_grape_hpc.png}`
- `tests/test_exp143.py` (`9` yazılım regresyon testi)
