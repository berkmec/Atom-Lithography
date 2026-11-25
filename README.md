# Atom Litografi Makinesi (v7.2)

TRL 1–2 (`M0`) Kavramsal Sistem Tasarımı, İndirgenmiş-Mertebe Çok-Fizikli Fizibilite Çalışması, Gerçek-EDA Doğrulamalı Verilog RTL ve Bulut Süperiletken-QPU Kontrol/Dekoder Kıyaslaması

Doğrudan Artefaktlar: [**180/180 Parça Mühendislik Planı (`hardware/DESIGN_BLUEPRINT_180_SUMMARY.md`)**](hardware/DESIGN_BLUEPRINT_180_SUMMARY.md) · [**164-Parça Ana Montaj Paftası (`hardware/cad_parts/master_164_assembly_views.png`)**](hardware/cad_parts/master_164_assembly_views.png) · [Makine-Kontrol RTL (`rtl/machine_ctrl/README.md`)](rtl/machine_ctrl/README.md) · [Etkileşimli HTML5 Model Gezgini (`docs/digital_twin_interactive.html`)](docs/digital_twin_interactive.html) · [BOED Verilog RTL (`rtl/boed_fpga/README.md`)](rtl/boed_fpga/README.md) · [Ana Tasarım (`DESIGN.md`)](research/atom_lithography_machine/DESIGN.md) · [Teknik El Kitabı (`TECHNICAL_MANUAL.md`)](research/atom_lithography_machine/TECHNICAL_MANUAL.md)

---

## Özet

Atom Litografi Makinesi (`v7.2`), zenginleştirilmiş `²⁸Si` üzerinde deterministik tek-atom donör yerleşimi ve hata-toleranslı ölçekleme için geliştirilmiş **`TRL 1–2` (`M0`) düzeyinde kavramsal bir sistem mimarisi ve indirgenmiş-mertebe çok-fizikli fizibilite çalışmasıdır**. Depo, `28` ön-kayıtlı sayısal çalışmayı (`Exp124`–`Exp151`), konak makinede gerçek açık-kaynak EDA araçlarıyla (`iverilog 14.0`, `verilator 5.055`, `yosys 0.71+101`; `no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`) doğrulanmış `1.193` satırlık sentezlenebilir IEEE 1364-2005 `Q16.16` BOED-FPGA Verilog RTL modüllerini, gerçek `1% ²⁹Si` elmas-kübik örgü banyosu BOED kıyaslamasını (`results/boed_real_bath_benchmark.json`), fiziksel ODE/PDE/Lindblad/GF(2) tabanlı `auto_recal.py` ve `programmer.py` çözücülerini, `SEMI S2` kılavuzları ve `IEC 61508 SIL-3` mimari hedeflerini referans alan sertifikasız bir `M0` ön emniyet FMEA/HAZOP taramasını (`iec61508_certified = false`, `semi_s2_certified = false`, `15`-durumlu `λ_DU × β` duyarlılık taraması), `199` parçalık nominal statik 3B CAD montajını ve `180` parçalık parametrik `BOM v7.0` (`10-RFQ` taslağı, `no_supplier_quotes = true`) paketini birleştirir. Seçili alt-çözücüler mikroskobik veya cebirsel denklemleri doğrudan çözer (`Exp136` `160k`-orbital `sp³d⁵s*` tight-binding, `Exp137/143` & `programmer.py` exact 16B Lindblad + Gillespie-OU `1/f`, `Exp138` MWPM, `Exp144/147` & `programmer.py` GF(2) `BP-OSD`); buna karşılık sistem düzeyindeki proses, emniyet, maliyet ve kapasite kestirimleri **parametrik/indirgenmiş-mertebe modellere ve literatür varsayımlarına** dayanır. Ayrıca `CellISA v4.0 → OpenQASM 3.0` kontrol derleyicisi, dinamik dekupling, `d=3` tekrar dekoderi ve bit-kesin `Q16.16` BOED algoritmaları `156`-kübitlik süperiletken `ibm_marrakesh` bulut QPU işlemcisinde kontrol/dekoder proxy kıyaslaması olarak çalıştırılmıştır (`Exp145`; silikon fabrikasyonunu doğrulamaz).

## Abstract

Atom Lithography Machine (`v7.2`) is a **`TRL 1–2` (`M0`) conceptual systems-architecture and reduced-order multiphysics feasibility study** for deterministic single-atom donor placement in enriched `²⁸Si` and fault-tolerant quantum scaling. The repository combines `28` preregistered numerical studies (`Exp124`–`Exp151`), `1,193`-LOC synthesizable IEEE 1364-2005 `Q16.16` BOED-FPGA Verilog RTL modules verified with real open-source EDA tools on host (`iverilog 14.0`, `verilator 5.055`, `yosys 0.71+101`; `no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`), a real `1% ²⁹Si` diamond-cubic lattice-bath BOED benchmark (`results/boed_real_bath_benchmark.json`), physics-based ODE/PDE/Lindblad/GF(2) solvers in `auto_recal.py` and `programmer.py`, an uncertified `M0` preliminary parametric safety FMEA/HAZOP screening (`iec61508_certified = false`, `semi_s2_certified = false`, `15`-case `λ_DU × β` PFD sensitivity sweep and RK4 ODH box-ODE transient), a `199`-part nominal static 3D CAD assembly, and a parametric `180`-part `BOM v7.0` (`10-RFQ` draft, `no_supplier_quotes = true`). Specific sub-solvers evaluate microscopic or algebraic physics (`Exp136` `160k`-orbital `sp³d⁵s*` tight-binding, exact 16D Lindblad + Gillespie-OU `1/f` master equations, `Exp138` MWPM, GF(2) Bivariate Bicycle `BP-OSD`), whereas system-level process, safety, cost, and throughput estimates rely on **parametric/reduced-order models and literature assumptions**. Separately, the `CellISA v4.0 → OpenQASM 3.0` compiler, dynamical decoupling, `d=3` repetition decoding, and bit-exact `Q16.16` BOED routines were executed on the `156`-qubit superconducting `ibm_marrakesh` cloud QPU as a non-silicon control/decoder proxy (`Exp145`).

---

## Bu Depo Neyi Gösterir, Neyi Kanıtlamaz? (Scope: Demonstrated vs. Not Demonstrated)

| Alan | Gösterilen (Demonstrated) | Kanıtlanmayan (Not Demonstrated) |
|---|---|---|
| Bulut QPU (`Exp145`, `ibm_marrakesh`) | `CellISA v4.0 → OpenQASM 3.0` derleyici, `Echo / XY4`, `d=3` tekrar dekoderi ve `Q16.16` BOED algoritmalarının süperiletken transmon bulut işlemcisinde (`job_id = dc1tdo2nj2vs73dfrfl0`) çalıştırıldığını gösterir. | Silikon `³¹P` implantasyonu, flaş tavlama, MBE, `100 K` IBIC veya herhangi bir atom-litografi donanımını doğrulamaz. |
| Gerçek Açık-Kaynak EDA RTL Doğrulaması (`Exp149`, `rtl/boed_fpga/`) | `verilator 5.055 --lint-only -Wall` (`0` uyarı/hata), `iverilog 14.0 + vvp` (`64/64` vektör + `4`-kanal AXI4-Stream `0 LSB`, `584` çevrim, `0` kombinasyonel `/`) ve `yosys 0.71+101` ön-P&R sentezi (`xcup`/`xc7`/`ecp5`; `no_external_eda_sim = false`, `real_eda_verified = true`). | Ticari Xilinx Vivado P&R zamanlama kapanışı (`no_vendor_vivado_pnr = true`) ve fiziksel `ZU48DR` FPGA kart ölçümü (`no_lab_measurement_rtl = true`) henüz yapılmamıştır. |
| Yazılım Regresyon Testleri (`333/333` temiz klon `pytest`; yerel çalışma alanında `400/400`) | Kod tabanının yeniden üretilebilirliğini, birim doğruluğunu, açık-kaynak EDA eş-doğrulamasını ve iç sayısal tutarlılığını gösterir (temiz `git clone`: `35/35` staged Atom Litografi suiti = `333/333`; `.gitignore` dışı `12` yerel eski `quantum_cell` suitiyle toplam `400/400`). | Fiziksel modelin gerçek laboratuvar koşullarında doğru olduğunu kanıtlamaz. |
| Dosya Bütünlüğü (`39/39 SHA-256`, `v7_digital_twin_cert.json`) | Üretilen artefaktların sonradan değiştirilmediğini doğrulayan dosya-bütünlüğü ve izlenebilirlik özetidir. | Bilimsel doğrulama, hakemli onay veya endüstriyel sertifikasyon değildir. |
| Fizik, `1% ²⁹Si` Banyo & Maliyet Modellemesi (`Exp124`–`Exp151`) | Seçili alt-çözücülerde atomistik/cebirsel hesabı (`sp³d⁵s*` TB, exact 16B Lindblad + Gillespie-OU, `45.214` konumlu `1% ²⁹Si` elmas-kübik banyo, MWPM, GF(2) BP-OSD, doğrusal-olmayan Si termal PDE, 2-oda UHV ODE) sistem düzeyinde parametrik analizle birleştirir; tüm ön-kayıtlı `FAIL` ve başarısızlık duvarlarını (`2 kHz` Fourier duvarı, `SNR ≤ 3` uçurumu, `%61,51` dürüst step-and-stitch verimi) korur. | Uçtan uca deneysel fiziksel doğrulama veya tedarikçi teklifi değildir (`no_lab_measurement = true`, `no_supplier_quotes = true`, `tapeout_done = false`). |
| Emniyet Analizi (`Exp150`, `PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED`) | `25` satırlı ön `M0` tehlike taraması (`FMEA`), `10` düğümlü `HAZOP`, `15`-durumlu `1oo2D` `λ_DU × β` duyarlılık taraması (`10× λ_DU @ β=%10 → SIL-2`'ye düşüş), RK4 oda ODH kutu-ODE geçişi ve hedeflenen kilitleme bütçesidir. | Sertifikasyon değildir (`iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`); SEMI kendi S2 kılavuzu için sertifika vermez, IEC 61508 SIL-3 ise tedarikçi FMEDA verisi, tam emniyet yaşam döngüsü ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir. |
| 3B CAD (`199` parça, `0/19.701` çakışma, `40/40` boşluk) | Yalnızca nominal statik geometrik çakışma ve zarf kontrolüdür. | Üretilebilirlik (`DFM`), GD&T tolerans yığılması, `300 K → 20 mK` termal büzülme, titreşim kuplajı, kablo/tesisat yönlendirme, UHV gaz salınımı, manyetik malzeme uyumu veya montaj sırası doğrulaması değildir. |
| Simülasyonda `FAIL → PASS` İterasyonları (`Exp139`, `Exp141`, `Exp148`) | Kendi model uzayında yapılan tasarım ve parametre iterasyonlarını belgeler (`1440 K → 1530,1 K`, `W2/W3` SOI, `¹²¹Sb` `Q-Echo-8`). | Deneysel fiziksel engel giderimi veya laboratuvar doğrulaması değildir. |
| Üretim Kapasitesi ve `MachineConfig` (`2,95×10⁹` atış/gün, `1,50–2,25×10⁹` yazmaç/gün) | Varsayılan model girdileri (`detector_eta = 0,9994`, `bath_yield = 0,51`, `spot_sigma_nm = 1,5 nm`, `readout_visibility = 0,99`) altında hesaplanan koşullu matematiksel üst-sınır kapasitesidir; `%5` ölü blanker kanalında dürüst step-and-stitch verimi `%61,51`'dir. | Fiziksel bir makinede ölçülmüş üretim hızı (throughput) değildir. |

> [!NOTE]
> **Ön-Kayıtlı Hükümler:** Tüm deneylerde başarı ölçütleri hesaplamadan önce `predictions_exp*.json` dosyalarına kaydedilmiştir. Karşılanmayan tüm `FAIL` hükümleri (`Exp124, 126, 127, 128 [v7 Full], 129, 131, 134, 136, 137, 138, 139, 142, 143, 147 [UQ4, UQ5], 148 [SQ4]`) gizlenmeden ve kök-nedeniyle raporlanmıştır.

---

## Genel Görünüm

### 164-Parça Bütünleşik Mühendislik Ana Montaj Paftası (`v8.0-blueprint`, `0 / 13.366` 3B Çakışma, `M0/M1 DESIGN_ONLY`)

![Atom Litografi Makinesi 164-Parça Bütünleşik Mühendislik Ana Montaj Paftası (Front XZ, Side YZ, Plan XY, İzometrik, Hassas Çekirdek Kesiti ve Kütle Bütçesi)](hardware/cad_parts/master_164_assembly_views.png)

> **180 / 180 Parça Mühendislik Planı (`hardware/parts_registry.json`, `M0/M1_DESIGN_ONLY`):** `164/164` su-sızdırmaz 6-formatlı CAD (`.stl`, ISO 10303-21 `.step`, `.dxf`, `librsvg` doğrulamalı GD&T `.svg`, `.scad`, `.json`; `718.532` üçgen, `0/13.366` küresel çakışma, `2.996,77 kg`, `30/30` NIST kriyo termal, `10/10` GD&T) · `%100` pad'den pad'e fiziksel rotalı `10/10` KiCad 8 PCB (`762/762` ağ, `9.895` segment, `2.538` via, `0` ERC/DRC/HV) + `10/10` canlı `ngspice-47` + `95/95` elektrik ICD · `7` makine-kontrol Verilog RTL modülü (`3.212` LOC, `Verilator 0` uyarı, `Icarus 6/6`, `Yosys xcup/xc7/ecp5`) · `S8.4-02` SCADA & `S8.2-02` OpenROAD manifestosu. Detay: [`hardware/DESIGN_BLUEPRINT_180_SUMMARY.md`](hardware/DESIGN_BLUEPRINT_180_SUMMARY.md).

### Kavramsal Sistem Özet Panosu (`v7.2`)

![Atom Litografi Makinesi v7.2 M0 Kavramsal Tasarım Özet Panosu](research/atom_lithography_machine/cad/drawings/00_v7_overview_dashboard.png)

| İzometrik Nominal 3B Montaj (`199` Parça) | Nominal Statik Kesit (`40/40` Zarf) | Patlatılmış Alt-Sistem Görünümü (`S1`–`S7`) |
|---|---|---|
| [![3B Önizleme](research/atom_lithography_machine/cad/preview_machine.png)](research/atom_lithography_machine/cad/preview_machine.png) | [![Kesit](research/atom_lithography_machine/cad/drawings/09_atom_litho_cutaway.png)](research/atom_lithography_machine/cad/drawings/09_atom_litho_cutaway.png) | [![Patlatılmış](research/atom_lithography_machine/cad/drawings/10_atom_litho_exploded.png)](research/atom_lithography_machine/cad/drawings/10_atom_litho_exploded.png) |

---

## 1. Sistem Özeti ve Başlıca Model Parametreleri (`v7.2`, `TRL 1–2 / M0`)

| Parametre | Model Çıktısı / Tasarım Hedefi | Kaynak / Deney |
|---|---|---|
| Yerleştirme belirsizliği (`5 keV ³¹P⁺`, `Arch-B`) | `σ_tot = 3,59–3,63 nm` (`1530,1 K` flaş + `S5.6` MBE modeli) | `Exp124`, `Exp139` |
| Titreşim ve işaret kararlılığı (`S6.9 CFG4`) | `σ_stage = 0,102 nm`, `σ_pointing = 0,147 nm` (modal/PSD modeli) | `Exp133` |
| Flaş tavlama ve epitaksiyel kapsülleme (`S5.5`, `S5.6`) | `1530,1 K` / `1,0 ms`, `8 nm` LT-MBE, `S_ε = 0,390 µeV/√Hz` | `Exp130`, `Exp139` |
| Paralel yazma ve tek-kriyostat kapasitesi | `32×32 = 1.024` demetçik; `2.887` hücre (`N_mux* = 32`, `F_RO = %99,61`); koşullu üst-sınır `2,95×10⁹` atış/gün (`%5` ölü kanalda dürüst step-and-stitch verimi `%61,51`, `%100` kapsama) | `Exp124`, `Exp140`, `auto_recal.py` |
| Gerçek `1% ²⁹Si` örgü banyosu BOED (`N = 260`) | `%91,15` vs `%84,62` Uniform (`10,46×` prob / `26,29×` zaman hızlanması, `A_par RMSE = 96,17 Hz`, eski `Exp132` `%100` FNR; dürüst `2 kHz` Fourier duvarı & `SNR ≤ 3` uçurumu) | `boed_real_bath_benchmark.json` |
| `M4` iki-kübit kapı modeli (`3 kΩ NbTiN`, `D3` GRAPE) | `p_2q = %0,337–%0,395`, `Λ = 2,825`, `100G` RDMA `BP-OSD 2,32 µs`; `programmer.py` exact 16B Lindblad + Gillespie-OU Echo-CZ (`F_Bell = 0,9804`, `+0,212` kazanç) & GF(2) BB qLDPC | `Exp137`, `Exp143`, `programmer.py` |
| `qLDPC` bellek (`[[144,12,12]]` Gross Code) | `L_max = 268,3 µm ≤ 300 µm`, `108L = 1` kriyostat (`$63.827/L_sys` model) | `Exp144` |
| Evrensel `qLDPC` (`[[288,12,18]]`) ve `T`-fabrikası | `p_th = %0,781`, `576`-hücre verimi `%99,27` (`N=8`) / `%99,82` (`N=9`) | `Exp147` |
| Algoritmik kaynak bütçeleri (FeMoco ve `RSA-2048`) | FeMoco: `16` kriyostat (`3,38 sa`, `$6.537/çözüm`, dürüst `UQ5` tavanı); `RSA-2048`: `291` kriyostat (`7,37 MW`, `21,1 sa`) | `Exp147` |
| `¹²¹Sb` (`I=7/2`) kudit koruma ve `SU(8)` kontrol | `Q-Echo-8` statik `0,5800 → 0,99908` (`455,5×` hata azalması); `SU(8)` `≥ 0,9954`; `1/f` `Q-Echo-64` `28,08×` (`1,45 ms`) | `Exp148` |
| Gerçek-EDA doğrulamalı Verilog RTL (`rtl/boed_fpga/`) | `4` modül (`1.193` LOC, `0` `/` bölücü), `verilator 5.055 -Wall` `0` uyarı, `iverilog 14.0` `64/64` + `4`-ch `0 LSB` / `584` çevrim (`2,336 µs`), `yosys 0.71` `xcup_top16` `102.886` LUT (`%24,19`), `59.157` FF (`%6,96`), `192` RAMB18 (`%8,89`), `1.584` DSP (`%37,08`) (`no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`) | `Exp149` |
| Ön emniyet taraması (sertifikasız `M0` parametrik hesap) | `iec61508_certified = false`, `semi_s2_certified = false`, `25` FMEA `max RPN 280 → 42`, nominal `PFD = 2,34×10⁻⁵` (`15`-durumlu `λ_DU × β` taraması: `10× λ_DU @ β=%10 → 1,22×10⁻³` `SIL-2`), RK4 ODH `60 m³ 0 ACH = %20,57`, `S7.SAFETY $145k` | `Exp150` |
| Nominal 3B CAD ve parametrik `BOM v7.0` (`10-RFQ` taslağı) | `199` CAD parçası (yalnız nominal statik: `1.108,14 kg` şasi + `355,0 kg` tesis), `180` BOM parçası, Faz-1 `Base+Safety $5,393M` (`%4,67`), `v7 Full $5,693M` (`%5,22`) | `Exp128 v7.0`, `Exp151` |

---

## 2. Kavramsal Sistem Mimarisi (`TRL 1–2 / M0`)

```mermaid
flowchart LR
    A["1. İyon Kaynağı ve Ön Emniyet<br/>S1+S2: 32×32 Demetçik, S1-Multi<br/>S7.SAFETY: Ön Emniyet Hedefi (Sertifikasız)"] --> B["2. Algılama ve Tavlama Modeli<br/>S3: 100 K IBIC (η=%99,94)<br/>S5: 1530,1 K Flaş + 8 nm MBE"]
    B -->|"Kapanış Tetiği"| A
    B -->|"W2/W3 SOI Modeli"| C["3. 20 mK İşlemci ve RTL<br/>S6: 1,50 T, N_mux*=32, qRAM<br/>S7: Q16.16 BOED RTL (584 çevrim)"]
    C -->|"D3 GRAPE + RDMA"| D["4. FT QEC ve Bulut QPU Proxy<br/>[[288,12,18]] qLDPC + T-Fabrikası<br/>CellISA v4.0 + ibm_marrakesh Proxy"]
    C -->|"auto_recal sim"| A
```

---

## 3. Sürüm Evrimi (`v3.0`–`v7.2`)

| Sürüm | Temel Modelleme ve Yazılım Değişimi | Nominal CAD / Parametrik BOM | `pytest` |
|---|---|---|---|
| `v3.0` (`Exp124`–`Exp128`) | `10→5 keV` iyon optiği, `1,50 T / 22,3 µT` ayrıştırma, 32B GRAPE, `100 K` IBIC (`0` ERC), ilk MC BOM | `143` parça / `$4,19M` | `89` |
| `v4.0` (`Exp129`–`Exp135`) | `VOKL-6` vadi-yörünge analizi, `S5.5` flaş tavlama, `3 kΩ` `M4` cQED, `BOED` (`24,4×`), `S6.9` titreşim modeli, 5y TCO | `170` parça / `$4,61M` | `142` |
| `v5.0` (`Exp136`–`Exp141`) | `160k`-orbital `sp³d⁵s*` TB (`f*=%1,5`), yankılı `P4` `M4` kapısı, `1530,1 K` + `S5.6` MBE, `Q16.16` BOED, `N_mux*=32`, `W2/W3` SOI | `189` parça / `$5,25M` | `198` |
| `v6.0` (`Exp142`–`Exp146`) | `Option-Q` (`S1-Multi` + `qRAM`), `D3` GRAPE + `Option-HPC` RDMA, `[[144,12,12]]` `qLDPC` (`108L=1` kriyo), `ibm_marrakesh` QPU kontrol proxy | `199` parça / `$5,55M` (`9-RFQ`) | `252` |
| `v7.0` / `v7.1` (`Exp147`–`Exp151`) | Evrensel `[[288,12,18]]` + `T`-fabrikası, `¹²¹Sb` `Q-Echo-8` (`455,5×`), Verilog RTL + HTML5 gezgin, sertifikasız `M0` FMEA/HAZOP (`RFQ-10`), `v7.1` epistemik bütünlük temizliği | `199` parça (+`355 kg` tesis) / `180p` Faz-1 `$5,39M` · Full `$5,69M` (`10-RFQ` taslağı) | `306` |
| `v7.2` (Gerçek EDA + `1% ²⁹Si` Banyo + Fizik) | Gerçek açık-kaynak EDA (`iverilog`/`verilator -Wall`/`yosys` `xcup`/`xc7`/`ecp5`, `1.193` LOC, `0` `/` bölücü, `no_external_eda_sim=false`), gerçek `1% ²⁹Si` örgü banyosu BOED (`%91,15`, `10,46×` prob), fiziksel `auto_recal`/`programmer` (UHV ODE, Si PDE, `%61,51` stitch, exact 16B Lindblad+Gillespie-OU, GF(2) BB qLDPC), `Exp150` `λ_DU×β` taraması + RK4 ODH | `199` parça (+`355 kg` tesis) / `180p` (`39/39` `SHA-256`) | `333` (`400` tam) |

---

## 4. Bulut Süperiletken QPU Kontrol/Dekoder Kıyaslaması — Silikon Fabrikasyonunu Doğrulamaz (`ibm_marrakesh`, `156Q`)

`Exp145` kapsamında `CellISA v4.0` (`20` opcode) derleyicisi tarafından üretilen `16` adet `OpenQASM 3.0` devresi (`4.096` ölçüm/devre, `q2`–`q6` zinciri) süperiletken `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, çalışma süresi `32,54 s`) bulut işlemcisinde kontrol/dekoder proxy kıyaslaması olarak yürütülmüştür. Bu koşum yalnızca derleyici, dinamik dekupling, `d=3` sendrom dekoderi ve sabit-noktalı `Q16.16` BOED yazılım yığınını sınar; silikon `³¹P` implantasyonu, flaş tavlama, MBE veya atom-litografi donanımı hakkında hiçbir deneysel kanıt sağlamaz.

| Test | Çevrimdışı Heron Modeli | Bulut QPU Proxy (`ibm_marrakesh`) | Kapsam Notu |
|---|---|---|---|
| `C1` Dinamik Dekupling (`48,13 µs`) | Bare `0,5625` → Echo `0,8428` / XY4 `0,8591` (`+29,7 pp`) | Bare `0,3325` → Echo `0,9224` / XY4 `0,9280` (`+59,5 pp`) | Transmon üzerinde `XY4` zamanlama hizalaması |
| `C1` Bell Durumu (`Φ+`) | `F(Φ+) = 0,9530` | `F(Φ+) = 0,9733` (`⟨ZZ⟩=0,9614`, `⟨XX⟩=0,9717`, `⟨YY⟩=−0,9600`) | Yerel `cz` kapı derlemesi kontrolü |
| `C2` `d=3` Tekrar Kodu (`3,97 µs`) | `p_phys = 0,0297` → MWPM `0,0039` (`7,61×`), çoğunluk `0,0020` (`15,23×`) | `p_phys = 0,0296` → MWPM `0,0057` (`5,16×`), çoğunluk `0,0038` (`7,83×`) | Sendrom son-seçiminde `0/7.451` hata (`%90,95` tutma) |
| `C3` `Q16.16` BOED Ramsey (`125 kHz`) | `3` nokta `125,852 kHz` (`\|Q16.16 − FP64\| = 0,7 Hz`) | `3` nokta `120,106 kHz` (`\|Q16.16 − FP64\| = 1,6 Hz`) | `q2` doğal kayması `−4,52 kHz` (8-nokta referansla uyumlu) |

---

## 5. Modüler Alt-Sistemler (`S1`–`S9`), Nominal 3B CAD ve Parametrik Fazlı Maliyet (`BOM v7.0`)

`BOM.csv` (`$2,531M`) tarihsel baz olarak korunur; `BOM_DETAILED.csv v7.0` (`180` parça, `no_supplier_quotes = true`) `$0,00` iç mutabakat ve `0,0000 kg` nominal şasi kütle eşleşmesiyle parametrik bütçe tahmini sunar. Modelde **Faz-1 (`M3 Base+Safety`, `173` parça, `$5.392.800`, ön emniyet kiti sertifikasız `M0`)** `P(Prog > $100M) = %4,67 < %5` (`6/6 CU PASS`) koşulunu sağlar; `RFQ-05` fiyat kilidi sonrasında **Faz-2 (`+Option-Q` / `+Option-HPC`)** ile `v7 Full` (`$5.692.800`) yapılandırması öngörülür.

| Kod | Alt-Sistem | Nominal CAD Parça / Kütle | `M3 v7.0 Full` / `M1 Base` | RFQ Taslağı | Bağlantılar |
|---|---|---:|---:|---|---|
| `S1` | `10→5 keV` Kolon ve `S1.7` `S1-Multi` | `13` / `30,78 kg` | `$484.000` / `$319.750` | `RFQ-01`, `09` | [`.scad`](research/atom_lithography_machine/cad/parts/s1_ion_source_column.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s1_ion_source_column.stl) · [Pafta `01`](research/atom_lithography_machine/cad/drawings/01_s1_ion_source_column.png) |
| `S2` | `32×32` (`0,50 mm`) MEMS Yazma Kafası | `9` / `1,83 kg` | `$775.500` / `$147.750` | `RFQ-02` | [`.scad`](research/atom_lithography_machine/cad/parts/s2_mems_write_head.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s2_mems_write_head.stl) · [Pafta `02`](research/atom_lithography_machine/cad/drawings/02_s2_mems_write_head.png) |
| `S3` | `100 K` Soğuk-Ada IBIC Ön-Uç (`0` ERC) | `7` / `0,15 kg` | `$224.000` / `$88.550` | Özel PCB | [`.scad`](research/atom_lithography_machine/cad/parts/s3_ibic_detector_assembly.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s3_ibic_detector_assembly.stl) · [Pafta `03`](research/atom_lithography_machine/cad/drawings/03_s3_ibic_detector_assembly.png) · [`BOARD.md`](src/board/BOARD.md) |
| `S4` | Granit, 6-DOF Piezo, `Zerodur/Invar-36` | `18` / `302,37 kg` | `$253.000` / `$233.920` | `RFQ-03` | [`.scad`](research/atom_lithography_machine/cad/parts/s4_piezo_stage_interferometry.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s4_piezo_stage_interferometry.stl) · [Pafta `04`](research/atom_lithography_machine/cad/drawings/04_s4_piezo_stage_interferometry.png) |
| `S5` | UHV (`34,86 L`), `S5.5` Flaş ve `S5.6` MBE | `29` / `193,94 kg` | `$433.000` / `$358.300` | `RFQ-07A`, `08` | [`.scad`](research/atom_lithography_machine/cad/parts/s5_uhv_chamber_loadlock.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s5_uhv_chamber_loadlock.stl) · [Pafta `05`](research/atom_lithography_machine/cad/drawings/05_s5_uhv_chamber_loadlock.png) |
| `S6` | DR, `S6.9`, Mıknatıs, `M4`, `S6.5` MUX, `qRAM` | `105` / `285,32 kg` | `$2.794.100` / `$1.171.150` | `RFQ-04`–`09` | [`.scad`](research/atom_lithography_machine/cad/parts/s6_cryo_dr_magnet_readout.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s6_cryo_dr_magnet_readout.stl) · [Pafta `06`](research/atom_lithography_machine/cad/drawings/06_s6_cryo_dr_magnet_readout.png) |
| `S7`–`S9` | Kontrol, Verilog RTL, `S7.SAFETY` (sertifikasız `M0`), `Option-HPC` | `18` / `293,75 kg` (+`355 kg` tesis) | `$729.200` / `$146.700` (`M1+S +$145k`) | `RFQ-09`, `10` | [`.scad`](research/atom_lithography_machine/cad/parts/s7_electronics_rack_interconnect.scad) · [`.stl`](research/atom_lithography_machine/cad/stl/s7_electronics_rack_interconnect.stl) · [Pafta `07`](research/atom_lithography_machine/cad/drawings/07_s7_electronics_rack_interconnect.png) · [`src/README.md`](src/README.md) · [`rtl/boed_fpga/`](rtl/boed_fpga/README.md) |
| Toplam | Ana Montaj (`ALM-600-00`) ve `BOM v7.0` (`180p`) | `199` / `1.108,14 kg` + `355,0 kg` tesis | Faz-1 `$5.392.800` · Full `$5.692.800` / `M1 $2.466.120` | `10-RFQ` (`%78,2` / `%92,6` MC) | [Ana `.scad`](research/atom_lithography_machine/cad/atom_litho_machine.scad) · [Ana `.stl`](research/atom_lithography_machine/cad/stl/atom_litho_machine.stl) · [Montaj `08`](research/atom_lithography_machine/cad/drawings/08_atom_litho_assembly.png) · [`BOM_DETAILED.csv`](research/atom_lithography_machine/BOM_DETAILED.csv) |

---

## 6. Ön-Kayıtlı Sayısal Çalışma Defteri (`Exp124`–`Exp151`)

Her deneyin tahminleri hesaplamadan önce `predictions_exp*.json` içine dondurulmuş, karşılanmayan hükümler (`FAIL`) kök-nedeniyle korunmuştur. Simülasyon iterasyonlarında `FAIL → PASS` geçişleri yalnızca model uzayındaki tasarım değişikliklerini temsil eder; deneysel doğrulama değildir.

| Deney | Kapsam | Hüküm | Başlıca Model Bulgusu / Kısıt | Artefaktlar |
|---|---|---|---|---|
| `Exp124` | `10→5 keV` iyon kolonu ve 3B donör saçılması | `6/8 PASS, 2/8 FAIL` | `CD3 FAIL` (`κ_c ≥ 4,67` → `Arch-B` + `HDA-HiRes`); `CD7 FAIL` (`z>0` Holmes `%69,5`); Mod B bağışık | [`summary_exp124.md`](results/exp124_ion_column_optics/summary_exp124.md) · [`test_exp124.py`](tests/test_exp124.py) |
| `Exp125` | `1,50 T / 22,3 µT` mıknatıs, termal ve `R8` | `6/6 PASS` | `R7` manyetik ayrıştırma model uzayında giderildi (`22,3 µT`, `64,6 K` quench); `1 K` Mod B `3,40×` yavaş | [`summary_exp125.md`](results/exp125_cryo_magnet_readout/summary_exp125.md) · [`test_exp125.py`](tests/test_exp125.py) |
| `Exp126` | 32B CUDA `XY8`-GRAPE ve 16-hücre programı | `5/8 PASS, 3/8 FAIL` | `P126_1..3 FAIL` (`q3` köşe/MC); Risk `R3` model uzayında giderildi (`N=32` `0,926 / 0,965`, `N=128` elendi) | [`summary_exp126.md`](results/exp126_atom_cell_programming/summary_exp126.md) · [`test_exp126.py`](tests/test_exp126.py) |
| `Exp127` | `100 K` soğuk-ada IBIC ve `CellISA v2.0` | `4/6 PASS, 2/6 FAIL` | `CZ3,4 FAIL`: Lindhard `5 keV` RT `200 ns` verimi `%9,7` → `COLD_100K` (`η = %99,94`) seçildi | [`summary_exp127.md`](results/exp127_detector_frontend_sim/summary_exp127.md) · [`test_detector_frontend.py`](tests/test_detector_frontend.py) |
| `Exp128` (`v7.0`) | `180` parça parametrik `BOM v7.0`, `10-RFQ` ve 100k MC | `6/6` (Faz-1); `v7 Full CU3 FAIL` | `10-RFQ = %78,24` nom / `%92,58` var; Faz-1 `Base+Safety $5,39M (%4,67 PASS)`; `v7 Full $5,69M (%5,22 FAIL)` | [`summary_exp128.md`](results/exp128_bom_sensitivity/summary_exp128.md) · [`test_bom_detailed.py`](tests/test_bom_detailed.py) |
| `Exp129` | `VOKL-6` 6-vadi merkez-hücre (`R1`) | `3/7 PASS, 4/7 FAIL` | `CE3,4,6,7 FAIL`: `R331 = %64,73`, `HM5962 = %33,25` → `Exp136` atomistik TB ve `M1 G6b` gereksinimi | [`summary_exp129.md`](results/exp129_valley_orbital_hyperfine/summary_exp129.md) · [`test_exp129.py`](tests/test_exp129.py) |
| `Exp130` | `S5.5` `808 nm / 1,0 ms` flaş tavlama (`R6`) | `6/6 PASS` | Fırın/RTA elendi; `1440 K` `σ_anneal = 0,328 nm` (sonra `Exp139`'da `1530,1 K` tasarım iterasyonu) | [`summary_exp130.md`](results/exp130_flash_anneal_diffusion/summary_exp130.md) · [`test_exp130.py`](tests/test_exp130.py) |
| `Exp131` | `M4` `3 kΩ NbTiN` cQED ve 2B perkolasyon | `4/7 PASS, 3/7 FAIL` | `CM3,4,6 FAIL`: `3 kΩ` `F_Bell = 0,9655` (`0,359 µs`); yalın `CZ = 0,777` → `Exp137` yankı kapısı | [`summary_exp131.md`](results/exp131_scalable_m4_architecture/summary_exp131.md) · [`test_exp131.py`](tests/test_exp131.py) |
| `Exp132` | `BOED` spektroskopi ve `CellISA v3.0` | `6/6 PASS` | `41,03 ms` (`24,37×`, `RMS = 72,67 Hz`); `CellISA v3.0` `4×4` `F_joint = 0,9834` | [`summary_exp132.md`](results/exp132_bayesian_spectroscopy_cellisa3/summary_exp132.md) · [`test_exp132.py`](tests/test_exp132.py) |
| `Exp133` | `S6.9` `PT420` titreşim/FEM/termal ayrıştırma | `8/8 PASS` | Rijit `PT420` `2.052 nm` sapar → `CFG4` + `Zerodur/Invar-36`: `σ_stage = 0,102 nm`, `σ_pointing = 0,147 nm` | [`summary_exp133.md`](results/exp133_coupled_vibration_thermal/summary_exp133.md) · [`test_exp133.py`](tests/test_exp133.py) |
| `Exp134` | 5y TCO, birim ekonomi ve Wright öğrenme | `5/6 PASS, 1/6 FAIL` | `CX4 FAIL`: `W1` `²⁸Si` yonga `%92,2` taban oluşturur → `Exp141` `W2/W3` SOI senaryosuyla modelde giderildi | [`summary_exp134.md`](results/exp134_fab_economics_tco/summary_exp134.md) · [`test_exp134.py`](tests/test_exp134.py) |
| `Exp135` | `v4.0` birleşik artefakt özeti | `7/7 PASS` | `11/11` JSON `SHA-256` dosya bütünlüğü özeti ve `Exp131 × Exp129` `N_cand*` mutabakatı | [`summary_exp135.md`](results/exp135_v4_digital_twin/summary_exp135.md) · [`test_exp135.py`](tests/test_exp135.py) |
| `Exp136` | `160k`-orbital `sp³d⁵s*` TB ve optimal `f*` | `4/7 PASS, 3/7 FAIL` | `TB4,5,7 FAIL`; `R331 %64,73 → %21,1`, `f*=%1,5 + 2 MV/m → %77,50` (`%99,88 M4`), `XY8 T₂e = 10,8–20,3 ms` | [`summary_exp136.md`](results/exp136_tb_sp3d5s_hyperfine/summary_exp136.md) · [`test_exp136.py`](tests/test_exp136.py) |
| `Exp137` | Yankılı `P4` `M4` `CZ` (`1/f^α` CUDA) | `4/7 PASS, 3/7 FAIL` | `EC2,4,5 FAIL`: pasivesiz `S_ε = 1,0` yetersiz (`0,9587`); Rota C ile `F_Bell = 0,9949`, `p_err = %0,92` | [`summary_exp137.md`](results/exp137_echoed_m4_bus_gate/summary_exp137.md) · [`test_exp137.py`](tests/test_exp137.py) |
| `Exp138` | `d=3..11` kusurlu yüzey kodu MWPM FT | `6/7 PASS, 1/7 FAIL` | `FT5 FAIL` (`f=%1` `%79,0`) → `f*=%1,5 + N=6` `%99,5`; `p_2q,th = %1,60`, `D2 Λ=1,40`, `D3 Λ=2,52` | [`summary_exp138.md`](results/exp138_defective_surface_code_ft/summary_exp138.md) · [`test_exp138.py`](tests/test_exp138.py) |
| `Exp139` | `8 nm` MBE, gizli TED, `1530,1 K` ve `S5.6` | `4/7 PASS, 3/7 FAIL` | `EP3,5,7 FAIL`: `v4` `1440 K` `+1,318 nm` TED (`3,995 nm`) → `1530,1 K` (`3,665 nm`) + `S5.6` MBE (`S_ε=0,390`, model iterasyonu) | [`summary_exp139.md`](results/exp139_epi_cap_process_integration/summary_exp139.md) · [`test_exp139.py`](tests/test_exp139.py) |
| `Exp140` | `Q16.16` FPGA, `N_mux*=32` ve `CellISA v3.5` | `7/7 PASS` | `2,336 µs/adım`, `N_mux*=32` (`F_RO=%99,61`), tek kriyostat `2.887` hücre, `CellISA v3.5`, `S6.5` | [`summary_exp140.md`](results/exp140_cryo_fpga_boed_mux_readout/summary_exp140.md) · [`test_exp140.py`](tests/test_exp140.py) |
| `Exp141` | `v5.0` bütünleşik artefakt özeti ve `CX4` SOI | `8/8 PASS` | `19/19` `SHA-256` dosya bütünlüğü, `W2/W3` SOI senaryosuyla `CX4 PASS` (`−%79,5 / −%85,3`), `D3 10⁻⁹` `$2,76M` | [`summary_exp141.md`](results/exp141_v5_digital_twin/summary_exp141.md) · [`test_exp141.py`](tests/test_exp141.py) |
| `Exp142` | `Option-Q` `qRAM` ve `S1-Multi` (`¹⁶⁷Er`/`¹²¹Sb`) | `5/7 PASS, 2/7 FAIL` | `OQ5,6 FAIL` (`¹²¹Sb` gerinim/derinlik); `qRAM 8.403×–25.122×` ömür (`+0,78 µW`), `10 km` `¹⁶⁷Er` `1.352 Hz` | [`summary_exp142.md`](results/exp142_option_q_multispecies_qram/summary_exp142.md) · [`test_exp142.py`](tests/test_exp142.py) |
| `Exp143` | `D3` `K=8` GRAPE `M4` ve `Option-HPC` RDMA | `4/7 PASS, 3/7 FAIL` | `DH1..3 FAIL` (muhafazakar/sızıntı); yankılı `p_2q = %0,337–%0,395`, `Λ = 2,825`, `qLDPC 2,32 µs` | [`summary_exp143.md`](results/exp143_d3_grape_m4_and_hpc_decoder/summary_exp143.md) · [`test_exp143.py`](tests/test_exp143.py) |
| `Exp144` | `[[144,12,12]]` Gross Code `qLDPC` | `7/7 PASS` | `L_max = 268,3 µm ≤ 300 µm` (`0` rezonatör değişikliği), `N=8` `%99,94`, `108L = 1` kriyostat (`$63.827/L_sys`) | [`summary_exp144.md`](results/exp144_qldpc_bivariate_bicycle_m4/summary_exp144.md) · [`test_exp144.py`](tests/test_exp144.py) |
| `Exp145` | Bulut `156Q` `ibm_marrakesh` kontrol proxy ve `CellISA v4.0` | `7/7 PASS` | `dc1tdo2nj2vs73dfrfl0` (`0` sızıntı, silikon-dışı proxy): XY4 `0,9280`, Bell `0,9733`, `d=3` `5,16× / 7,83×`, `BOED 1,6 Hz` | [`summary_exp145.md`](results/exp145_cloud_qpu_ibm_validation/summary_exp145.md) · [`test_exp145.py`](tests/test_exp145.py) |
| `Exp146` | `v6.0` bütünleşik artefakt özeti (`24/24` + QPU) | `8/8 PASS` | `24/24` + proxy QPU `SHA-256` dosya bütünlüğü özeti, `679 → 100 → 1` kriyostat sıkıştırma modeli | [`summary_exp146.md`](results/exp146_v6_digital_twin/summary_exp146.md) · [`test_exp146.py`](tests/test_exp146.py) |
| `Exp147` | Evrensel `[[288,12,18]]` `qLDPC`, `T`-fabrikası, FeMoco/RSA | `5/7 PASS, 2/7 FAIL` | `UQ4,5 FAIL` (okuma tavanı `p_meas ≤ %0,15`); FeMoco `16` kriyo (`37,1×`, `3,38 sa`), `RSA-2048` `291` kriyo (`52,7×`, `7,37 MW`) | [`summary_exp147.md`](results/exp147_universal_qldpc_d18_magic_state/summary_exp147.md) · [`test_exp147.py`](tests/test_exp147.py) |
| `Exp148` | `¹²¹Sb` `I=7/2` `Q-Echo-8` ve `SU(8)` GRAPE | `6/7 PASS, 1/7 FAIL` | `SQ4 FAIL` (Cywiński `1/f`); `OQ6` model uzayında giderildi: statik Gross `0,5800 → 0,99908` (`455,5×`), `SU(8) ≥ 0,9954` | [`summary_exp148.md`](results/exp148_sb121_quadrupole_echo_qudit/summary_exp148.md) · [`test_exp148.py`](tests/test_exp148.py) |
| `Exp149` | Gerçek-EDA doğrulamalı Verilog RTL ve HTML5 gezgin | `8/8 PASS` | `no_external_eda_sim=false`, `no_vendor_vivado_pnr=true`; `1.193` LOC (`0` `/` bölücü), `verilator -Wall` `0` uyarı, `iverilog` `64/64` + `4`-ch `0 LSB` / `584` çevrim, `yosys` `xcup_top16` (`102.886` LUT, `1.584` DSP, `96` BRAM36) + `78,7 KB` HTML5 gezgin | [`summary_exp149.md`](results/exp149_boed_verilog_rtl_and_interactive_twin/summary_exp149.md) · [`test_exp149.py`](tests/test_exp149.py) |
| `Exp150` | Ön emniyet taraması `FMEA/HAZOP` (sertifikasız `M0`) | `7/7 PASS` | `iec61508_certified=false`, `semi_s2_certified=false`, `25` FMEA `max RPN 280 → 42`, `15`-durumlu `λ_DU×β` taraması (`10×@β=%10 → SIL-2`), RK4 ODH, `S7.SAFETY $145k` (`RFQ-10`) | [`summary_exp150.md`](results/exp150_industrial_safety_fmea_hazop/summary_exp150.md) · [`test_exp150.py`](tests/test_exp150.py) |
| `Exp151` | `v7.2` bütünleşik artefakt özeti (`39/39` `SHA-256`) | `8/8 PASS` | `39/39` dosya bütünlüğü `SHA-256` manifestosu (gerçek EDA + `1% ²⁹Si` banyo + fiziksel `auto_recal`/`programmer` + sertifikasız `Exp150`), Faz-1 `$5,39M` → Faz-2 `$5,69M`, `400/400` (`333` AL) `pytest` | [`summary_exp151.md`](results/exp151_v7_digital_twin/summary_exp151.md) · [`test_exp151.py`](tests/test_exp151.py) |

---

## 7. Görseller ve Teknik Çizimler

<details open>
<summary>v7.0 / v7.2 Şekilleri (Exp147–Exp151, 5 adet 2400×1400 PNG)</summary>

| `Exp147` Evrensel `[[288,12,18]]` `qLDPC` ve FeMoco / `RSA-2048` | `Exp148` `¹²¹Sb` `Q-Echo-8` ve `SU(8)` GRAPE |
|---|---|
| ![Exp147 Universal qLDPC](results/exp147_universal_qldpc_d18_magic_state/fig_exp147_universal_qldpc_magic.png) | ![Exp148 121Sb Q-Echo](results/exp148_sb121_quadrupole_echo_qudit/fig_exp148_sb121_qudit_echo.png) |
| `Exp149` Gerçek-EDA `Q16.16` BOED-FPGA Verilog RTL (`584` Çevrim) | `Exp150` Ön Emniyet Hedefi `FMEA/HAZOP` (`RPN 280→42`, Sertifikasız `M0`) |
| ![Exp149 Verilog RTL](results/exp149_boed_verilog_rtl_and_interactive_twin/fig_exp149_rtl_fpga_arch.png) | ![Exp150 Industrial Safety](results/exp150_industrial_safety_fmea_hazop/fig_exp150_safety_fmea_hazop.png) |

| `Exp151` Bütünleşik Artefakt Özeti ve Dosya Bütünlüğü (`39/39` `SHA-256`) Panosu |
|---|
| ![Exp151 v7 Twin](results/exp151_v7_digital_twin/fig_exp151_v7_digital_twin.png) |

</details>

<details>
<summary>v6.0 Şekilleri (Exp142–Exp146, 5 adet 2400×1400 PNG)</summary>

| `Exp142` `Option-Q` `qRAM` ve `S1-Multi` (`¹⁶⁷Er`/`¹²¹Sb`) | `Exp143` `D3` `K=8` GRAPE `M4` ve `Option-HPC` `100G` RDMA |
|---|---|
| ![Exp142 Option-Q](results/exp142_option_q_multispecies_qram/fig_exp142_option_q_multispecies.png) | ![Exp143 D3 HPC](results/exp143_d3_grape_m4_and_hpc_decoder/fig_exp143_d3_grape_hpc.png) |
| `Exp144` `[[144,12,12]]` `qLDPC` Tek-Kriyostat Modeli | `Exp145` Bulut `156Q` `ibm_marrakesh` Kontrol Proxy ve `auto_recal` |
| ![Exp144 qLDPC](results/exp144_qldpc_bivariate_bicycle_m4/fig_exp144_qldpc_m4.png) | ![Exp145 Live IBM QPU](results/exp145_cloud_qpu_ibm_validation/fig_exp145_ibm_qpu_live.png) |

| `Exp146` `v6.0` Artefakt Özeti Panosu |
|---|
| ![Exp146 v6 Twin](results/exp146_v6_digital_twin/fig_exp146_v6_digital_twin.png) |

</details>

<details>
<summary>Nominal Statik CAD Paftaları (CAD v6.0 ALM-600, 8 adet 2400×1600 PNG)</summary>

| `S1` İyon Kolonu ve `S1-Multi` (`ALM-600-S1`) | `S2` MEMS Yazma Kafası (`ALM-600-S2`) |
|---|---|
| ![S1](research/atom_lithography_machine/cad/drawings/01_s1_ion_source_column.png) | ![S2](research/atom_lithography_machine/cad/drawings/02_s2_mems_write_head.png) |
| `S3` Soğuk-Ada IBIC (`ALM-600-S3`) | `S4` Piezo ve İnterferometri (`ALM-600-S4`) |
| ![S3](research/atom_lithography_machine/cad/drawings/03_s3_ibic_detector_assembly.png) | ![S4](research/atom_lithography_machine/cad/drawings/04_s4_piezo_stage_interferometry.png) |
| `S5` UHV, `S5.5` Flaş ve `S5.6` MBE (`ALM-600-S5`) | `S6` DR, MUX ve `Option-Q` qRAM (`ALM-600-S6`) |
| ![S5](research/atom_lithography_machine/cad/drawings/05_s5_uhv_chamber_loadlock.png) | ![S6](research/atom_lithography_machine/cad/drawings/06_s6_cryo_dr_magnet_readout.png) |
| `S7` Elektronik ve `Option-HPC` RDMA (`ALM-600-S7`) | Ana Montaj (`ALM-600-00`) |
| ![S7](research/atom_lithography_machine/cad/drawings/07_s7_electronics_rack_interconnect.png) | ![Ana](research/atom_lithography_machine/cad/drawings/08_atom_litho_assembly.png) |

</details>

<details>
<summary>v5.0–v3.0 Destekleyici Şekiller (Exp124–Exp141, 31 adet PNG)</summary>

| `Exp136` `160k`-Orb `sp³d⁵s*` TB ve Optimal `f*` | `Exp137` `1/f^α` Yankılı `P4` `M4` `CZ` Faz Haritası |
|---|---|
| ![Exp136 TB](results/exp136_tb_sp3d5s_hyperfine/fig_exp136_tb_hyperfine_f_opt.png) | ![Exp137 Echo](results/exp137_echoed_m4_bus_gate/fig_exp137_echoed_m4_bus.png) |
| `Exp138` `d=3..11` Kusurlu Yüzey Kodu MWPM FT | `Exp139` `1530,1 K` TED İterasyonu ve `S5.6` MBE Rota C |
| ![Exp138 FT](results/exp138_defective_surface_code_ft/fig_exp138_surface_code_ft.png) | ![Exp139 MBE](results/exp139_epi_cap_process_integration/fig_exp139_epi_cap_integration.png) |
| `Exp140` `Q16.16` FPGA, `N_mux*=32` ve Kriyo Tavanı | `Exp141` `v5.0` Artefakt Özeti ve `CX4` SOI |
| ![Exp140 FPGA](results/exp140_cryo_fpga_boed_mux_readout/fig_exp140_fpga_mux_cryo.png) | ![Exp141 Twin](results/exp141_v5_digital_twin/fig_exp141_v5_digital_twin.png) |
| `Exp129` `VOKL-6` 6-Vadi ENDOR Kabukları | `Exp129` `VOKL-6` vs `KL` Mod B Verim |
| ![Exp129 ENDOR](results/exp129_valley_orbital_hyperfine/fig_exp129_endor_shells.png) | ![Exp129 Yield](results/exp129_valley_orbital_hyperfine/fig_exp129_vokl6_yield.png) |
| `Exp130` `S5.5` Flaş Tavlama Penceresi | `Exp130` TED Difüzyon Profilleri |
| ![Exp130 Window](results/exp130_flash_anneal_diffusion/fig_exp130_anneal_window.png) | ![Exp130 TED](results/exp130_flash_anneal_diffusion/fig_exp130_profiles_ted.png) |
| `Exp131` `M4` `3 kΩ NbTiN` vs `50 Ω` cQED | `Exp131` 2B Kare vs Heavy-Hex Perkolasyon |
| ![Exp131 cQED](results/exp131_scalable_m4_architecture/fig_exp131_m4_bus_fidelity.png) | ![Exp131 Perc](results/exp131_scalable_m4_architecture/fig_exp131_2d_percolation.png) |
| `Exp132` `BOED` Spektroskopi Hızlanması | `Exp132` `4×4` Yönlendirme ve `CellISA v3.0` |
| ![Exp132 BOED](results/exp132_bayesian_spectroscopy_cellisa3/fig_exp132_bayesian_speedup.png) | ![Exp132 CellISA3](results/exp132_bayesian_spectroscopy_cellisa3/fig_exp132_wafer_routing_cellisa3.png) |
| `Exp133` `PT420` Birleşik PSD ve Kolon FEM | `Exp133` `CFG1` vs `CFG4` İzolasyon Bütçesi |
| ![Exp133 PSD](results/exp133_coupled_vibration_thermal/fig_exp133_psd_jitter.png) | ![Exp133 Budget](results/exp133_coupled_vibration_thermal/fig_exp133_isolation_budget.png) |
| `Exp134` 5y TCO ve Birim Kübit Ekonomisi | `Exp134` `v3.0` vs `v4.0` Wright Öğrenme |
| ![Exp134 TCO](results/exp134_fab_economics_tco/fig_exp134_tco_cost_per_qubit.png) | ![Exp134 Scaling](results/exp134_fab_economics_tco/fig_exp134_v3_vs_v4_scaling.png) |
| `Exp135` `v4.0` Artefakt Özeti Panosu | `Exp124` Optik Zarf ve Scherzer Sınırı |
| ![Exp135 Digital Twin](results/exp135_v4_digital_twin/fig_exp135_v4_digital_twin.png) | ![Exp124 Optics](results/exp124_ion_column_optics/fig_exp124_optics_envelope.png) |
| `Exp124` 3B Anizotropik ve Stokastik Donör Verimi | `Exp125` `1,50 T / 22,3 µT` Manyetik Alan Haritası |
| ![Exp124 Yield](results/exp124_ion_column_optics/fig_exp124_anisotropic_yield.png) | ![Exp125 Bfield](results/exp125_cryo_magnet_readout/fig_exp125_bfield_map.png) |
| `Exp125` 5-Kademe Termal, RF SNR ve `R8` Koiller | `Exp126` 32B GRAPE Darbeleri ve DDRF Kurtarma |
| ![Exp125 Thermal](results/exp125_cryo_magnet_readout/fig_exp125_thermal_snr.png) | ![Exp126 Pulses](results/exp126_atom_cell_programming/fig_exp126_grape_pulses.png) |
| `Exp126` İç-İçe `XY8` vs `Exp63` ve `CPMG` | `Exp126` 16 Heterojen Hücre × 5 Kuantum Programı |
| ![Exp126 DD](results/exp126_atom_cell_programming/fig_exp126_interleaved_dd_vs_exp63.png) | ![Exp126 MultiCell](results/exp126_atom_cell_programming/fig_exp126_multicell_programs.png) |
| `Exp127` IBIC Blok Şeması (`COLD_100K`, `0` ERC) | `Exp127` Sonlu-GBP Bode ve Zaman-Domeni Yanıtı |
| ![Exp127 Schematic](results/exp127_detector_frontend_sim/fig_exp127_schematic_block.png) | ![Exp127 Bode](results/exp127_detector_frontend_sim/fig_exp127_bode_transient.png) |
| `Exp127` Lindhard ENC ve 50k MC Algılama Verimi | `Exp128` `M1` vs `M3` Maliyet ve `10-RFQ` Kırılımı |
| ![Exp127 MC](results/exp127_detector_frontend_sim/fig_exp127_enc_eta_mc.png) | ![Exp128 M1M3](results/exp128_bom_sensitivity/fig_exp128_m1_vs_m3_cost.png) |

| `Exp128` 100k MC Tornado ve Kümülatif Dağılım (CDF) |
|---|
| ![Exp128 Tornado](results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png) |

</details>

---

## 8. Etkileşimli Artefaktlar, Yazılım Regresyon Testleri ve Dosya Bütünlüğü

- **Çevrimdışı HTML5 Model Gezgini:** [`docs/digital_twin_interactive.html`](docs/digital_twin_interactive.html) (`78,7 KB` / `78.675` bayt, `5` sekme, `0` harici CDN/HTTP çağrısı; yerel tarayıcıda doğrudan açılır).
- **Gerçek-EDA Doğrulamalı Verilog RTL:** [`rtl/boed_fpga/README.md`](rtl/boed_fpga/README.md) (`4` sentezlenebilir IEEE 1364-2005 modülü = `1.193` satır, `0` kombinasyonel `/` bölücü, `verilator 5.055 -Wall` `0` uyarı/hata, `iverilog 14.0 + vvp` `64/64` + `4`-ch `0 LSB` / `584` çevrim, `yosys 0.71` `xcup`/`xc7`/`ecp5`; `no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`).
- **Gerçek `1% ²⁹Si` Örgü Banyosu BOED Kıyaslaması:** [`results/boed_real_bath_benchmark.json`](results/boed_real_bath_benchmark.json) (`45.214` elmas-kübik örgü konumu, `N = 260`, `%91,15` vs `%84,62` Uniform, `10,46×` prob / `26,29×` zaman hızlanması, dürüst `2 kHz` Fourier duvarı & `SNR ≤ 3` uçurumu).

### Yazılım Regresyon Testleri (Temiz Klon: `333/333` [`35/35` Suit]; Yerel Geliştirme Alanı: `400/400`)

Aşağıdaki komut yalnızca kod tutarlılığını, birim doğruluğunu, açık-kaynak EDA eş-doğrulamasını ve iç yeniden üretilebilirliği sınar; fiziksel laboratuvar doğrulaması değildir. Temiz bir `git clone` bu depodaki **`35/35` staged Atom Litografi test dosyasını (`333/333 PASS`)** yürütür; `.gitignore` tarafından yayın paketinin dışında tutulan `12` yerel eski `quantum_cell` test dosyasını (`67` test) da barındıran yerel geliştirme çalışma alanında aynı `tests/` taraması **`400/400 PASS`** verir.

```bash
git clone https://github.com/berkmec/Atom-Lithography.git
cd Atom-Lithography
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Temiz git clone (35/35 staged Atom Litografi test dosyası -> 333/333 PASS):
PYTHONPATH=.:src python3 -B -m pytest tests/ -v -p no:cacheprovider

# (Yalnızca .gitignore dışı 12 yerel eski quantum_cell suitini içeren tam yerel geliştirme alanında -> 400/400 PASS):
# PYTHONPATH=.:src python3 -B -m pytest tests/ --ignore=tests/test_chain_phonon.py --ignore=tests/test_fem.py -v -p no:cacheprovider
```

### İsteğe Bağlı Yeniden Üretim Komutları

```bash
# 1. CellISA v4.0 + BOED (--preset v400) simülasyonu:
PYTHONPATH=src python3 -m machine_control.sim --slots 4000 --preset v400 --program bell --program-mode grape

# 2. Q16.16 BOED-FPGA gerçek EDA (iverilog/verilator/yosys) doğrulaması ve HTML5 model gezgini derleme:
PYTHONPATH=.:src python3 experiments/exp149_boed_verilog_rtl_and_interactive_twin/run_exp149.py

# 3. Nominal parametrik CAD v6.0 STL, geometri JSON ve özet panosu:
python3 research/atom_lithography_machine/cad/gen_scad.py
python3 research/atom_lithography_machine/cad/gen_stl.py
python3 research/atom_lithography_machine/cad/gen_v7_dashboard.py

# 4. Parametrik BOM v7.0, Exp128 100k MC ve Exp151 dosya bütünlüğü manifestosu (39/39 SHA-256):
python3 experiments/exp128_bom_sensitivity/build_bom_detailed.py
python3 experiments/exp128_bom_sensitivity/run_exp128.py
PYTHONPATH=.:src python3 experiments/exp151_v7_digital_twin/run_exp151.py
```

### Dosya Bütünlüğü ve İzlenebilirlik Özeti (`SHA-256` — Bilimsel Kanıt Değil)

Aşağıdaki `SHA-256` özetleri yalnızca depodaki çıktı dosyalarının sonradan değiştirilmediğini izlemek için kullanılan dosya-bütünlüğü özetleridir; bilimsel doğrulama veya sertifikasyon anlamı taşımaz.

| Artefakt | Kapsam | `SHA-256` Özeti |
|---|---|---|
| [`v7_digital_twin_cert.json`](results/exp151_v7_digital_twin/v7_digital_twin_cert.json) | `v7.2` bütünleşik dosya-bütünlüğü manifestosu (`Exp151`, `39/39` dosya) | `a72aa7150eb2c3407958671cb0f6a4eff6c21dc94deed799a88ca7e5fc32c3b8` |
| [`digital_twin_interactive.html`](docs/digital_twin_interactive.html) | Çevrimdışı HTML5 model gezgini (`78.675` bayt, `5` sekme) | `b252fa2c29f1901f13cc0773a83b89241e84931b0f00b75d79c7a41c1f02cc68` |
| [`boed_real_bath_benchmark.json`](results/boed_real_bath_benchmark.json) | Gerçek `1% ²⁹Si` elmas-kübik örgü banyosu BOED kıyaslaması (`N=260`) | `5ef83da01ffe635c362ec887a07f82ed043eaa03799403e3645e505551f055a8` |
| [`ibm_qpu_live_results.json`](results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json) | Bulut QPU proxy (`ibm_marrakesh`, `156Q`) ham sayım defteri | `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a` |
| [`v6_digital_twin_cert.json`](results/exp146_v6_digital_twin/v6_digital_twin_cert.json) | Tarihsel `v6.0` dosya-bütünlüğü manifestosu (`Exp146`) | `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7` |
| [`v5_digital_twin_cert.json`](results/exp141_v5_digital_twin/v5_digital_twin_cert.json) | Tarihsel `v5.0` dosya-bütünlüğü manifestosu (`Exp141`) | `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1` |
| [`v4_digital_twin_cert.json`](results/exp135_v4_digital_twin/v4_digital_twin_cert.json) | Tarihsel `v4.0` dosya-bütünlüğü manifestosu (`Exp135`) | `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57` |

---

## 9. Dokümantasyon Dizini

1. [`docs/digital_twin_interactive.html`](docs/digital_twin_interactive.html) ve [`rtl/boed_fpga/README.md`](rtl/boed_fpga/README.md) — Çevrimdışı etkileşimli model gezgini ve gerçek-EDA doğrulamalı `Q16.16` BOED-FPGA Verilog RTL paketi.
2. [`DESIGN.md`](research/atom_lithography_machine/DESIGN.md) — Ana kavramsal mimari tasarım belgesi (`v7.2`, `TRL 1–2 / M0`), risk matrisi ve sürüm günlüğü.
3. [`TECHNICAL_MANUAL.md`](research/atom_lithography_machine/TECHNICAL_MANUAL.md) — 12 bölümlü fizik, `CellISA v4.0`, `rtl/boed_fpga/`, nominal `CAD v6.0`, parametrik `BOM v7.0` / `10-RFQ` ve sertifikasız `M0` ön EHS el kitabı.
4. [`MODULAR.md`](research/atom_lithography_machine/MODULAR.md) — `M1`–`M8`, `Option-Q`, `Option-HPC` ve `S7.SAFETY` arayüz kontrol belgesi (`v7.2-ICD`).
5. [`M1_PROTOTYPE_BLUEPRINT.md`](research/atom_lithography_machine/M1_PROTOTYPE_BLUEPRINT.md) — İlk laboratuvar prototipi kavramsal planı (`M1 Base $2,466M`, `M1+Safety $2,611M`) ve `G1`–`G8` / `G6b` kabul kapıları.
6. [`BOM_ENGINEERING.md`](research/atom_lithography_machine/BOM_ENGINEERING.md) ve [`RFQ_SPECIFICATIONS.md`](research/atom_lithography_machine/RFQ_SPECIFICATIONS.md) — `180` parçalık parametrik malzeme listesi ve `10` tedarikçi ön RFQ taslağı (`no_supplier_quotes = true`).
7. [`PROJECT_DOSSIER.md`](research/atom_lithography_machine/PROJECT_DOSSIER.md) — `Exp0`–`Exp151` uçtan uca proje arşivi, bulut `ibm_marrakesh` kontrol proxy kıyaslaması ve nicel sicil.
8. [`LITERATURE.md`](research/atom_lithography_machine/LITERATURE.md) ve [`hypotheses.md`](research/hypotheses/hypotheses.md) — Birincil literatür/patent referansları ve `H1`–`H169` tam hipotez günlüğü.

---

## 10. Lisans (REUSE 3.3 Uyumlu Güçlü Karşılıklı Açık Kaynak / Copyleft)

**Copyright (C) 2026 berkmec (https://counfield.com/)**

Bu depo, tasarımın tüm insanlık için açık kalması ve bulut/SaaS, silikon/FPGA üretimi veya fiziksel donanım yoluyla kapatılıp tekelleştirilememesi amacıyla **`REUSE 3.3` uyumlu güçlü karşılıklı (*strongly reciprocal / copyleft*) üçlü lisans** ve çapraz-alan köprü dosyaları için **çift-copyleft (`OR`)** yapısını kullanır (ayrıntılı kapsam, `CERN-OHL-S v2` Bölüm 4 kaynak-konum etiketi zorunluluğu, Bölüm 8.3 sürüm hükmü ve marka koruması: [`NOTICE`](NOTICE) · makine-okunur SPDX eşlemesi: [`REUSE.toml`](REUSE.toml)):

| Kapsam | Lisans (SPDX) | Tam Metin |
|---|---|---|
| **Yazılım, Simülasyon, Kontrol Yığını, Testler, HTML5 Gezgin ve Depo Metaverisi** (`src/machine_control/**/*.py`, `experiments/**/*.py` [`build_bom_detailed.py` hariç], `tests/**/*.py`, `docs/digital_twin_interactive.html`, `requirements.txt`, `.gitignore`, `NOTICE`, `REUSE.toml`) | **GNU AGPLv3 veya üstü** (`AGPL-3.0-or-later` — bulut/SaaS ağ etkileşimi dâhil) | [`LICENSES/AGPL-3.0-or-later.txt`](LICENSES/AGPL-3.0-or-later.txt) · [`LICENSE`](LICENSE) |
| **Çapraz-Alan Donanım/RTL Üreteçleri, Derleme ve Veri/Spec Köprüsü** (`hardware/**/*.py`, `research/**/*.py`, `src/board/detector_frontend.py`, `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `rtl/**/Makefile`, `hardware/parts_registry.json`, `hardware/icd/parts/S8.*.json`, `BOM*.csv`, `cad_verification.json`, `results/**/*.json`, `results/**/*.jsonl`) | **Çift-Copyleft Köprü** (`AGPL-3.0-or-later OR CERN-OHL-S-2.0` — her iki seçim de kapatılamaz copyleft; çapraz lisans kilitlenmesini önler) | [`LICENSES/AGPL-3.0-or-later.txt`](LICENSES/AGPL-3.0-or-later.txt) · [`LICENSES/CERN-OHL-S-2.0.txt`](LICENSES/CERN-OHL-S-2.0.txt) |
| **Fiziksel Donanım ve Silikon/FPGA Verilog RTL** (`**/*.v`, `**/*.sv`, `**/*.xdc`, `**/*.hex`, `**/*.mem`, `**/*.ys`, `**/*.stl`, `**/*.step`, `**/*.scad`, `**/*.dxf`, `**/*.svg`, `**/*.kicad_pcb`, `**/*.kicad_sch`, `**/*.kicad_pro`, `**/*.cir`, `**/*.net` ve donanım `*.json` dosyaları) | **CERN Open Hardware Licence v2 — Strongly Reciprocal** (`CERN-OHL-S-2.0`, Bölüm 8.3 uyarınca v2 veya üstü `S` varyantı — PCB/CAD + FPGA/ASIC üretimi dâhil) | [`LICENSES/CERN-OHL-S-2.0.txt`](LICENSES/CERN-OHL-S-2.0.txt) |
| **Dokümantasyon, Bilimsel Raporlar ve Şekiller** (`**/*.md`, `**/*.png`) | **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`) | [`LICENSES/CC-BY-SA-4.0.txt`](LICENSES/CC-BY-SA-4.0.txt) |

Tüm materyaller ilgili lisans metinlerinde belirtildiği biçimde **"OLDUĞU GİBİ" (*AS IS*)** sunulur; donanım tasarımları `M0/M1 DESIGN_ONLY` aşamasındadır ve fonksiyonel emniyet sertifikası taşımaz. `berkmec` ve `https://counfield.com/` ad/alan adları için ticari onay veya marka hakkı devri verilmez.
