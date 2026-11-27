# Atom Litografi Makinesi (v7.2)

TRL 1–2 (`M0`) Kavramsal Sistem Tasarımı, İndirgenmiş-Mertebe Çok-Fizikli Fizibilite Çalışması, Gerçek-EDA Doğrulamalı Verilog RTL ve Bulut Süperiletken-QPU Kontrol/Dekoder Kıyaslaması

Doğrudan Artefaktlar: [**180/180 Parça Mühendislik Planı (`hardware/DESIGN_BLUEPRINT_180_SUMMARY.md`)**](hardware/DESIGN_BLUEPRINT_180_SUMMARY.md) · [**164-Parça Ana Montaj Paftası (`hardware/cad_parts/master_164_assembly_views.png`)**](hardware/cad_parts/master_164_assembly_views.png) · [Makine-Kontrol RTL (`rtl/machine_ctrl/README.md`)](rtl/machine_ctrl/README.md) · [Etkileşimli HTML5 Model Gezgini (`docs/digital_twin_interactive.html`)](docs/digital_twin_interactive.html) · [BOED Verilog RTL (`rtl/boed_fpga/README.md`)](rtl/boed_fpga/README.md) · [Ana Tasarım (`DESIGN.md`)](research/atom_lithography_machine/DESIGN.md) · [Teknik El Kitabı (`TECHNICAL_MANUAL.md`)](research/atom_lithography_machine/TECHNICAL_MANUAL.md)

---

## Özet

Atom Litografi Makinesi (`v7.2`), zenginleştirilmiş `²⁸Si` üzerinde deterministik tek-atom donör yerleşimi ve hata-toleranslı ölçekleme için geliştirilmiş **`TRL 1–2` (`M0/M1 DESIGN_ONLY`) düzeyinde kavramsal bir sistem mimarisi ve indirgenmiş-mertebe çok-fizikli fizibilite çalışmasıdır**. Depo, `28` ön-kayıtlı sayısal çalışmayı (`Exp124`–`Exp151`), konak makinede gerçek açık-kaynak EDA araçlarıyla (`iverilog 14.0`, `verilator 5.055`, `yosys 0.71+101`, `nextpnr-ecp5` vekili; `no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`) doğrulanmış sentezlenebilir IEEE 1364-2005 `Q16.16` BOED-FPGA ve makine-kontrol Verilog RTL modüllerini (`rtl/boed_fpga/`, `rtl/machine_ctrl/`, `rtl/cryo_crossbar_4k/`), gerçek `1% ²⁹Si` elmas-kübik örgü banyosu BOED kıyaslamasını (`results/boed_real_bath_benchmark.json`: `130,4 ms/aday`, `%91,15` doğruluk), fiziksel ODE/PDE/Lindblad/GF(2) tabanlı `auto_recal.py` ve `programmer.py` çözücülerini, `SEMI S2` kılavuzları ve `IEC 61508 SIL-3` mimari hedeflerini referans alan sertifikasız bir `M0` ön emniyet FMEA/HAZOP taramasını (`iec61508_certified = false`, `semi_s2_certified = false`, IEC 61508-6 `PFH` ve `15`-durumlu `λ_DU × β` duyarlılık taraması, `12,0 kWh` LFP UPS `202,8 dk @ %90 DoD`), **tek birleştirilmiş `164` fiziksel katı parçalık su-sızdırmaz 3B CAD ana montajını (`2.957,95 kg`, `0 / 13.366` çakışma, `32/32` kriyo termal, `10/10` GD&T; `10/10` KiCad 8 PCB `1.128/1.128` ağ `0` ERC/`0` DRC + `ngspice-47`)** ve `180` satırlık parametrik `BOM v7.0` (`10-RFQ` taslağı, `no_supplier_quotes = true`, `1.392/1.392` `%100` `SHA-256` sabitli `hardware/parts_registry.json`) paketini birleştirir. Seçili alt-çözücüler mikroskobik veya cebirsel denklemleri doğrudan çözerken sistem düzeyindeki proses, QEC (Stim devre eşiği `%0,60–%0,98`; `Exp147` `FeMoco d=18` ve `RSA-2048 d=24` `p_fail_total = 1,0`, `RSA-2048 d_req = 174,1`), emniyet, maliyet ve kapasite kestirimleri **parametrik/indirgenmiş-mertebe modellere ve literatür varsayımlarına** dayanır. Ayrıca `CellISA v4.0 → OpenQASM 3.0` kontrol derleyicisi, dinamik dekupling, `d=3` tekrar dekoderi ve bit-kesin `Q16.16` BOED algoritmaları `156`-kübitlik süperiletken `ibm_marrakesh` bulut QPU işlemcisinde kontrol/dekoder proxy kıyaslaması olarak çalıştırılmıştır (`Exp145`; silikon fabrikasyonunu doğrulamaz).

## Abstract

Atom Lithography Machine (`v7.2`) is a **`TRL 1–2` (`M0/M1 DESIGN_ONLY`) conceptual systems-architecture and reduced-order multiphysics feasibility study** for deterministic single-atom donor placement in enriched `²⁸Si` and fault-tolerant quantum scaling. The repository combines `28` preregistered numerical studies (`Exp124`–`Exp151`), synthesizable IEEE 1364-2005 `Q16.16` BOED-FPGA and machine-control Verilog RTL verified with real open-source EDA tools on host (`iverilog 14.0`, `verilator 5.055`, `yosys 0.71+101`, `nextpnr-ecp5` proxy; `no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`), a real `1% ²⁹Si` diamond-cubic lattice-bath BOED benchmark (`results/boed_real_bath_benchmark.json`: `130.4 ms/cand`, `91.15%` accuracy), physics-based ODE/PDE/Lindblad/GF(2) solvers in `auto_recal.py` and `programmer.py`, an uncertified `M0` preliminary parametric safety FMEA/HAZOP screening (`iec61508_certified = false`, `semi_s2_certified = false`, IEC 61508-6 PFH & `15`-case `λ_DU × β` sweep, upgraded `12.0 kWh` LFP UPS `202.8 min @ 90% DoD`), a **single reconciled `164`-part watertight 3D engineering CAD assembly (`2,957.95 kg`, `0 / 13,366` 3D solid clashes, `32/32` NIST cryo thermal checks, `10/10` GD&T stacks; `10/10` KiCad 8 PCBs `1,128/1,128` nets `0` ERC/`0` DRC + live `ngspice-47`)**, and a parametric `180`-row `BOM v7.0` (`10-RFQ` draft, `no_supplier_quotes = true`, `1,392/1,392` `100%` SHA-256 pinned in `hardware/parts_registry.json`). While selected sub-solvers evaluate microscopic or algebraic physics, system-level process, QEC (honest Stim circuit threshold `0.60–0.98%`; `Exp147` `FeMoco d=18` and `RSA-2048 d=24` yield `p_fail_total = 1.0` under D3 with `RSA-2048 d_req = 174.1`), safety, cost, and throughput estimates rely on **parametric/reduced-order models and literature assumptions**. Separately, the `CellISA v4.0 → OpenQASM 3.0` compiler, dynamical decoupling, `d=3` repetition decoding, and bit-exact `Q16.16` BOED routines were executed on the `156`-qubit superconducting `ibm_marrakesh` cloud QPU as a non-silicon control/decoder proxy (`Exp145`).

---

## Bu Depo Neyi Gösterir, Neyi Kanıtlamaz? (Scope: Demonstrated vs. Not Demonstrated)

| Alan | Gösterilen (Demonstrated) | Kanıtlanmayan (Not Demonstrated) |
|---|---|---|
| Bulut QPU (`Exp145`, `ibm_marrakesh`) | `CellISA v4.0 → OpenQASM 3.0` derleyici, `Echo / XY4`, `d=3` tekrar dekoderi ve `Q16.16` BOED algoritmalarının süperiletken transmon bulut işlemcisinde (`job_id = dc1tdo2nj2vs73dfrfl0`) çalıştırıldığını gösterir. | Silikon `³¹P` implantasyonu, flaş tavlama, MBE, `100 K` IBIC veya herhangi bir atom-litografi donanımını doğrulamaz. |
| Gerçek Açık-Kaynak EDA RTL & ASIC Durumu (`Exp149`, `rtl/boed_fpga/`, `rtl/machine_ctrl/`, `S8.2-02`) | `verilator 5.055 --lint-only -Wall` (`0` uyarı/hata), `iverilog 14.0 + vvp` (`64/64` vektör + `4`-kanal AXI4-Stream `0 LSB`, `584` çevrim, `0` kombinasyonel `/`), `yosys 0.71+101` (`xcup`/`xc7`/`ecp5`) ve `nextpnr-ecp5` (`LFE5U-85F` vekili: `boed_q16_core 43,58 MHz`, `fpga_top_carrier_wrap 79/205 TRELLIS_IO`); `no_external_eda_sim = false`, `real_eda_verified = true`. | Ticari Xilinx Vivado `ZU48DR`/`XC7K325T` P&R zamanlama kapanışı (`no_vendor_vivado_pnr = true`), fiziksel FPGA ölçümü (`no_lab_measurement_rtl = true`) ve SKY130 ASIC tape-out (`tapeout_done = false`, `PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY`, `Exp123 Attempt-2` geçersiz) henüz yapılmamıştır. |
| Yazılım Regresyon Testleri (**`620/620`** çıplak `pytest`, **`50`** takip edilen test dosyası) | Kod tabanının yeniden üretilebilirliğini, birim doğruluğunu, açık-kaynak EDA eş-doğrulamasını ve iç sayısal tutarlılığını gösterir (`35` v7.2 + `14` Stage-2 + `1` `test_qcell_legacy.py` = `50` takip edilen suit; çıplak `pytest -q`: `620 passed, 0 failed`, yeniden koşumda `0` dosya değişimi). | Fiziksel modelin gerçek laboratuvar koşullarında doğru olduğunu kanıtlamaz. |
| Dosya Bütünlüğü (`39/39` v7.2 + `1.392/1.392` Stage-2 `%100` `SHA-256`) | Üretilen artefaktların sonradan değiştirilmediğini doğrulayan dosya-bütünlüğü ve izlenebilirlik özetidir (`hardware/parts_registry.json`, `180/180` boş-olmayan ICD `verification_tests`). | Bilimsel doğrulama, hakemli onay veya endüstriyel sertifikasyon değildir. |
| Fizik, QEC (`Stim`/`Exp147`), `1% ²⁹Si` Banyo & Maliyet (`Exp124`–`Exp151`) | Atomistik/cebirsel hesabı (`sp³d⁵s*` TB, `16B` Lindblad + Gillespie-OU, `45.214` konumlu `1% ²⁹Si` banyo [`130,4 ms/aday`], Stim devre eşiği `%0,60–%0,98`, GF(2) BP-OSD, doğrusal-olmayan Si PDE, UHV ODE) sistem düzeyinde parametrik analizle birleştirir; tüm ön-kayıtlı `FAIL` ve fiziksel duvarları (`Exp147` `UQ4/UQ5/UQ6 FAIL`: `FeMoco d=18` & `RSA-2048 d=24` `p_fail_total = 1,0`, `RSA-2048 d_req = 174,1`; `CPU ldpc BP+OSD-2 34,7–181,7 ms`, sıfır QEC dekoder RTL; `2 kHz` Fourier duvarı; `SNR ≤ 3` uçurumu; `%61,51` step-and-stitch) korur. | Uçtan uca deneysel fiziksel doğrulama veya tedarikçi teklifi değildir (`no_lab_measurement = true`, `no_supplier_quotes = true`, `tapeout_done = false`). |
| Emniyet Analizi (`Exp150`, `PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED`) | `25` satırlı ön `M0` tehlike taraması (`FMEA`), `10` düğümlü `HAZOP`, IEC 61508-6 `PFH` & `15`-durumlu `1oo2D` `λ_DU × β` duyarlılık taraması, RK4 oda ODH geçişi (`60 m³ 0 ACH = %20,57`; havalandırmasız `≤15 m³` oda `%19,47 < %19,5` yasak), yükseltilmiş `12,0 kWh` LFP UPS (`202,8 dk @ %90 DoD ≥ 180 dk`) ve `≥150–200 °C` UHV fırınlama zorunluluğudur. | Sertifikasyon değildir (`iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`); SEMI kendi S2 kılavuzu için sertifika vermez, IEC 61508 SIL-3 ise tedarikçi FMEDA verisi, tam emniyet yaşam döngüsü ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir. |
| Birleşik 3B CAD (`164` fiziksel katı, `2.957,95 kg`, `0/13.366` çakışma) & `10/10` PCB (`0` ERC/`0` DRC) | `164/164` su-sızdırmaz STL/STEP/DXF/SVG (`756.540` üçgen, `32/32` NIST kriyo termal, `10/10` GD&T, `32/32` açık görüş hattı) ve `10/10` tam rotalı KiCad 8 PCB (`1.128/1.128` ağ, `0` ERC/`0` DRC + canlı `ngspice-47`) tasarım doğrulamasıdır (`180` BOM satırı). | Fiziksel üretim/laboratuvar doğrulaması veya tam 3B EM/FEM PCB/kavite son-onayı değildir (`OBS-074`: `ngspice`/analitik doğrulama 3B DOLFINx/openEMS/Palace parazitik/kavite analizinin yerini almaz; `no_lab_measurement = true`). |
| Simülasyonda `FAIL → PASS` İterasyonları (`Exp139`, `Exp141`, `Exp148`) | Kendi model uzayında yapılan tasarım ve parametre iterasyonlarını belgeler (`1440 K → 1530,1 K`, `W2/W3` SOI, `¹²¹Sb` `Q-Echo-8`). | Deneysel fiziksel engel giderimi veya laboratuvar doğrulaması değildir. |
| Üretim Kapasitesi ve `MachineConfig` (Koşullu Üst-Sınır vs. Düşürülmüş Gerçek Banyo) | `2,95×10⁹` atış/gün yalnızca varsayılan `MachineConfig` girdileri altındaki koşullu yazma üst-sınırıdır; gerçek `%1 ²⁹Si` banyo BOED `130,4 ms/aday` (`Exp132` `41,0 ms`'nin `3,18×` yavaşı) ve `%5` ölü blanker kanalında step-and-stitch verimi **`%61,51`**'e düşer. | Fiziksel bir makinede ölçülmüş üretim hızı (throughput) değildir. |

> [!NOTE]
> **Ön-Kayıtlı Hükümler:** Tüm deneylerde başarı ölçütleri hesaplamadan önce `predictions_exp*.json` dosyalarına kaydedilmiştir. Karşılanmayan tüm `FAIL` hükümleri (`Exp124, 126, 127, 128 [v7 Full], 129, 131, 134, 136, 137, 138 [FT3/FT5], 139, 142, 143 [DH1–DH5], 144 [QL4], 147 [UQ2, UQ4, UQ5, UQ6], 148 [SQ4]`) gizlenmeden ve kök-nedeniyle raporlanmıştır.

---

## Genel Görünüm

### 164-Parça Bütünleşik Mühendislik Ana Montaj Paftası (`v8.0-blueprint`, `2.957,95 kg`, `0 / 13.366` 3B Çakışma, `M0/M1 DESIGN_ONLY`)

![Atom Litografi Makinesi 164-Parça Bütünleşik Mühendislik Ana Montaj Paftası (Front XZ, Side YZ, Plan XY, İzometrik, Hassas Çekirdek Kesiti ve Kütle Bütçesi)](hardware/cad_parts/master_164_assembly_views.png)

> **180 / 180 Parça Mühendislik Planı (`hardware/parts_registry.json`, `M0/M1_DESIGN_ONLY`):** `164/164` su-sızdırmaz 6-formatlı CAD (`.stl`, ISO 10303-21 `.step`, `.dxf`, `librsvg` doğrulamalı GD&T `.svg`, `.scad`, `.json`; `756.540` üçgen, `0/13.366` küresel çakışma, **`2.957,9511 kg`** tek birleştirilmiş kütle, `32/32` NIST kriyo termal, `10/10` GD&T) · `%100` pad'den pad'e fiziksel rotalı `10/10` KiCad 8 PCB (`1.128/1.128` ağ, `12.883` segment, `3.495` via, `0` ERC/DRC/HV) + `10/10` canlı `ngspice-47` + `95/95` elektrik ICD (`12,0 kWh` LFP UPS `202,8 dk @ %90 DoD`) · `1.392/1.392` (`%100`) `SHA-256` sabitli + `180/180` boş-olmayan ICD `verification_tests` · `7` makine-kontrol Verilog RTL modülü (`3.212` LOC, `Verilator 0` uyarı, `Icarus 6/6`, `Yosys xcup/xc7/ecp5`, `nextpnr-ecp5` vekili) · `S8.4-02` SCADA & `S8.2-02` dürüst OpenROAD manifestosu (`PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY`). Detay: [`hardware/DESIGN_BLUEPRINT_180_SUMMARY.md`](hardware/DESIGN_BLUEPRINT_180_SUMMARY.md).

### Kavramsal Sistem Özet Panosu (`v7.2`)

![Atom Litografi Makinesi v7.2 M0 Kavramsal Tasarım Özet Panosu](research/atom_lithography_machine/cad/drawings/00_v7_overview_dashboard.png)

| Tarihsel `v6.0` Şematik Önizleme (Arşiv) | Tarihsel `v6.0` Kesit (Arşiv) | Tarihsel `v6.0` Patlatılmış Görünüm (Arşiv) |
|---|---|---|
| [![3B Önizleme](research/atom_lithography_machine/cad/preview_machine.png)](research/atom_lithography_machine/cad/preview_machine.png) | [![Kesit](research/atom_lithography_machine/cad/drawings/09_atom_litho_cutaway.png)](research/atom_lithography_machine/cad/drawings/09_atom_litho_cutaway.png) | [![Patlatılmış](research/atom_lithography_machine/cad/drawings/10_atom_litho_exploded.png)](research/atom_lithography_machine/cad/drawings/10_atom_litho_exploded.png) |

---

## 1. Sistem Özeti ve Başlıca Model Parametreleri (`v7.2`, `TRL 1–2 / M0`)

| Parametre | Model Çıktısı / Tasarım Hedefi | Kaynak / Deney |
|---|---|---|
| Yerleştirme belirsizliği (`5 keV ³¹P⁺`, `Arch-B`) | İndirgenmiş model `σ_tot = 3,59–3,63 nm`; gerçek sonsuz-alan ZBL/`iradina` 3B BCA `σ_lat = 4,39–4,44 nm` (`σ_tot = 4,76 nm > 3,80 nm`, dürüst fizik duvarı `OBS-039`) | `Exp124`, `Exp139` |
| Titreşim ve işaret kararlılığı (`S6.9 CFG4`) | `σ_stage = 0,102 nm`, `σ_pointing = 0,147 nm`; `S4.3-01` EDM fleksür CalculiX C3D10 `k_eff = 1,97–2,02 MN/m`, `13/13` açık optik LOS | `Exp133`, `s4_stage_metrology.py` |
| Flaş tavlama ve epitaksiyel kapsülleme (`S5.5`, `S5.6`) | `1530,1 K` / `1,0 ms`, `8 nm` LT-MBE, `S_ε = 0,390 µeV/√Hz`; `≥150–200 °C` UHV fırınlama zorunlu (fırınlamasız stres gaz salınımı `1,12×10⁻⁸ mbar`) | `Exp130`, `Exp139`, `OBS-124` |
| Paralel yazma ve tek-kriyostat kapasitesi | `32×32 = 1.024` demetçik; koşullu yazma üst-sınırı `2,95×10⁹` atış/gün (`%5` ölü kanalda dürüst step-and-stitch verimi **`%61,51`**; gerçek `%1 ²⁹Si` banyo BOED `130,4 ms/aday`) | `Exp124`, `Exp140`, `auto_recal.py` |
| Gerçek `1% ²⁹Si` örgü banyosu BOED (`N = 260`) | `%91,15` vs `%84,62` Uniform (`130,4 ms/aday`, `10,46×` prob / `26,29×` zaman hızlanması, `A_par RMSE = 96,17 Hz`, eski `Exp132` `%100` FNR; dürüst `2 kHz` Fourier duvarı & `SNR ≤ 3` uçurumu) | `boed_real_bath_benchmark.json` |
| `M4` iki-kübit kapı & QEC eşik gerçekliği | Gerçek Stim yüzey-kodu devre eşiği **`%0,60–%0,98`** (eski tur-başı `%1,60` değil); sentetik sıkıştırmasız 4×4 Tosi + Route C üst-eşikte (`Exp137`/`143` `HORIZON_TARGET_REQUIRED`); Option-HPC C++ `ldpc` `BP+OSD-2` `34,7–181,7 ms` (sıfır QEC dekoder RTL) | `Exp137`, `Exp138`, `Exp143`, `programmer.py` |
| `qLDPC` bellek (`[[144,12,12]]` Gross Code) | Cebir doğrulandı; düzlem-katlı yerleşimde `10.372` hava köprüsü ve `%26,4` `>300 µm` Manhattan aşımı (dürüst `QL4 FAIL` / Faz-3 Ar-Ge) | `Exp144` |
| Evrensel `qLDPC` (`[[288,12,18]]`) ve Algoritma Ufku | **`Exp147` dürüst `UQ2/UQ4/UQ5/UQ6 FAIL` (`3/7 PASS`)**: D3 altında `FeMoco d=18` ve `RSA-2048 d=24` ikisi de **`p_fail_total = 1,0`** (`RSA-2048 d_req = 174,1`); `16` / `291` kriyostat sayıları yalnızca `p_2q ≤ %0,15–%0,20` ve `p_meas ≤ %0,15` gerektiren ayak-izi alt-sınırlarıdır | `Exp147` |
| `¹²¹Sb` (`I=7/2`) kudit koruma ve `SU(8)` kontrol | `Q-Echo-8` statik `0,5800 → 0,99908` (`455,5×` hata azalması); `SU(8)` `≥ 0,9954`; `1/f` `Q-Echo-64` `28,08×` (`1,45 ms`); `B_M4 = 0,1785 T` spin karışımı dürüst sınır | `Exp148` |
| Gerçek-EDA doğrulamalı Verilog RTL & OpenROAD | `rtl/boed_fpga/` (`0` `/` bölücü, `verilator 5.055 -Wall` `0` uyarı, `iverilog` `64/64` `0 LSB` / `584` çevrim, `yosys` `xcup_top16` `102.886` LUT / `1.584` DSP) + `rtl/machine_ctrl/` (`3.212` LOC, `nextpnr-ecp5` vekili `boed_q16_core 43,58 MHz`, `fpga_top_carrier_wrap 79/205 TRELLIS_IO`; `no_vendor_vivado_pnr = true`) · SKY130 `S8.2-02` `PRE_FOUNDRY_NCH8_MACRO_PROTOTYPE_NOT_TAPEOUT_READY` (`tapeout_done = false`) | `Exp149`, `rtl_machine_ctrl_audit.json`, `openroad_signoff_manifest.json` |
| Ön emniyet taraması (sertifikasız `M0` parametrik hesap) | `iec61508_certified = false`, `semi_s2_certified = false`, `25` FMEA `max RPN 280 → 42`, IEC 61508-6 `PFH` & `15`-durumlu `λ_DU × β` taraması, RK4 ODH (`60 m³ 0 ACH = %20,57`; havalandırmasız `≤15 m³` oda `%19,47 < %19,5` yasak), **`12,0 kWh` LFP UPS `202,8 dk @ %90 DoD`** (`≥ 180 dk` PASS; `12,5 kW` PT420 şebeke tarafında), `S7.SAFETY $145k` | `Exp150`, `master_electrical_power_ups_budget.json` |
| Birleşik 3B CAD ve parametrik `BOM v7.0` (`10-RFQ` taslağı) | **`164` fiziksel katı CAD parçası (`2.957,95 kg`, `0/13.366` çakışma, `32/32` termal, `10/10` GD&T)**, `180` BOM satırı, `50 mm` FOAK pul kanonik baz, Faz-1 `Base+Safety $5,393M` (`P>$100M = %4,66 PASS`), `v7 Full $5,693M` (`%5,22` dürüst FAIL) | `cad_parts_verification.json`, `Exp128 v7.0`, `Exp151` |

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
| `v7.2` (Gerçek EDA + Birleşik 164p CAD + `1% ²⁹Si` Banyo + Fizik) | Gerçek açık-kaynak EDA (`iverilog`/`verilator -Wall`/`yosys` `xcup`/`xc7`/`ecp5` + `nextpnr-ecp5` vekili), gerçek `1% ²⁹Si` banyo BOED (`%91,15`, `130,4 ms/aday`), fiziksel `auto_recal`/`programmer`, dürüst Stim `%0,60–%0,98` / `Exp147` `p_fail_total=1,0`, `10/10` KiCad 8 PCB (`1.128/1.128` ağ, `0` ERC/DRC), `12,0 kWh` UPS (`202,8 dk @ %90 DoD`) | **`164` katı (`2.957,95 kg`, `0/13.366`)** / `180p` (`1.392/1.392` `SHA-256`) | **`620` (`50` takip edilen suit)** |

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

## 5. Modüler Alt-Sistemler (`S1`–`S9`), Birleşik 3B CAD (`164` Parça, `2.957,95 kg`) ve Parametrik Fazlı Maliyet (`BOM v7.0`)

`BOM.csv` (`$2,531M`) tarihsel baz olarak korunur; `BOM_DETAILED.csv v7.0` (`180` satır, `50 mm` FOAK kanonik pul, `no_supplier_quotes = true`) `$0,00` iç mutabakat ve **`hardware/cad_parts/cad_parts_verification.json` (`164` fiziksel katı parça, `2.957,9511 kg`, `0/13.366` çakışma, `32/32` termal, `10/10` GD&T)** ile tek birleştirilmiş mühendislik kütle bütçesini sunar (eski `v6.0` `199p / 1.108 kg` şematik CAD yalnızca tarihsel arşiv referansıdır). Modelde **Faz-1 (`M3 Base+Safety`, `173` satır, `$5.392.800`, ön emniyet kiti sertifikasız `M0`)** `P(Prog > $100M) = %4,66 < %5` (`6/6 CU PASS`) koşulunu sağlar; `RFQ-05` fiyat kilidi sonrasında **Faz-2 (`+Option-Q` / `+Option-HPC`)** ile `v7 Full` (`$5.692.800`, dürüst `%5,22 > %5`) yapılandırması öngörülür.

| Kod | Alt-Sistem | Birleşik CAD Katı / Kütle (`hardware/cad_parts/`) | `M3 v7.0 Full` / `M1 Base` | RFQ Taslağı | Bağlantılar |
|---|---|---:|---:|---|---|
| `S1` | `10→5 keV` Kolon ve `S1.7` `S1-Multi` | `23` / `331,76 kg` | `$484.000` / `$319.750` | `RFQ-01`, `09` | [`S1` CAD](hardware/cad_parts/out/S1/S1_manifest.json) · [Tarihsel Pafta `01`](research/atom_lithography_machine/cad/drawings/01_s1_ion_source_column.png) |
| `S2` | `32×32` (`0,50 mm`) MEMS Yazma Kafası | `15` / `11,06 kg` | `$775.500` / `$147.750` | `RFQ-02` | [`S2` CAD](hardware/cad_parts/out/S2/S2_manifest.json) · [Tarihsel Pafta `02`](research/atom_lithography_machine/cad/drawings/02_s2_mems_write_head.png) |
| `S3` | `100 K` Soğuk-Ada IBIC Ön-Uç (`0` ERC/DRC) | `14` / `38,43 kg` | `$224.000` / `$88.550` | Özel PCB | [`S3` CAD](hardware/cad_parts/out/S3/S3_manifest.json) · [`BOARD.md`](src/board/BOARD.md) |
| `S4` | Granit, 6-DOF EDM Piezo, `Zerodur/Invar-36` | `17` / `448,55 kg` | `$253.000` / `$233.920` | `RFQ-03` | [`S4` CAD](hardware/cad_parts/out/S4/S4_manifest.json) · [Tarihsel Pafta `04`](research/atom_lithography_machine/cad/drawings/04_s4_piezo_stage_interferometry.png) |
| `S5` | UHV (`34,86 L`), `S5.5` Flaş ve `S5.6` MBE | `23` / `266,23 kg` | `$433.000` / `$358.300` | `RFQ-07A`, `08` | [`S5` CAD](hardware/cad_parts/out/S5/S5_manifest.json) · [Tarihsel Pafta `05`](research/atom_lithography_machine/cad/drawings/05_s5_uhv_chamber_loadlock.png) |
| `S6` | DR, `S6.9`, Düzlem-İçi Mıknatıs, `M4`, `S6.5` MUX | `40` / `754,27 kg` | `$2.794.100` / `$1.171.150` | `RFQ-04`–`08` | [`S6` CAD](hardware/cad_parts/out/S6/S6_manifest.json) · [Tarihsel Pafta `06`](research/atom_lithography_machine/cad/drawings/06_s6_cryo_dr_magnet_readout.png) |
| `S7` | Kontrol Rafları, RTL, `S7.SAFETY` (`355,0 kg`, `12 kWh` UPS) | `19` / `821,00 kg` | `$349.200` / `$146.700` (`M1+S +$145k`) | `RFQ-08`, `10` | [`S7` CAD](hardware/cad_parts/out/S7/S7_manifest.json) · [`rtl/boed_fpga/`](rtl/boed_fpga/README.md) · [`rtl/machine_ctrl/`](rtl/machine_ctrl/README.md) |
| `S8` | Yazılım, Derleyici, RTL, OpenROAD & SCADA (`9` IN-HOUSE) | `0` / `0,00 kg` | `$0` / `$0` | IN-HOUSE | [`src/README.md`](src/README.md) · [`openroad_signoff_manifest.json`](hardware/eda_flow/openroad_signoff_manifest.json) |
| `S9` | Kalibrasyon, Yedekler, `Option-Q` & `Option-HPC` (`64,0 kg`) | `13` / `286,65 kg` | `$380.000` / `$0` | `RFQ-09` | [`S9` CAD](hardware/cad_parts/out/S9/S9_manifest.json) · [`DESIGN_BLUEPRINT_180_SUMMARY.md`](hardware/DESIGN_BLUEPRINT_180_SUMMARY.md) |
| **Toplam** | **Birleşik Ana Montaj (`164` Katı) ve `BOM v7.0` (`180` Satır)** | **`164` / `2.957,95 kg`** | **Faz-1 `$5.392.800` · Full `$5.692.800` / `M1 $2.466.120`** | **`10-RFQ` (`%78,2` / `%92,6` MC)** | [**164p Ana Pafta**](hardware/cad_parts/master_164_assembly_views.png) · [`parts_registry.json`](hardware/parts_registry.json) · [`BOM_DETAILED.csv`](research/atom_lithography_machine/BOM_DETAILED.csv) |

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
| `Exp147` | Evrensel `[[288,12,18]]` `qLDPC`, `T`-fabrikası, FeMoco/RSA | `3/7 PASS, 4/7 FAIL` | Dürüst `UQ2,4,5,6 FAIL`: D3 altında `FeMoco d=18` & `RSA-2048 d=24` `p_fail_total = 1,0` (`RSA-2048 d_req = 174,1`); `16` / `291` kriyo yalnızca `D3++` (`p ≤ %0,15–%0,20`) ayak-izi alt-sınırıdır | [`summary_exp147.md`](results/exp147_universal_qldpc_d18_magic_state/summary_exp147.md) · [`test_exp147.py`](tests/test_exp147.py) |
| `Exp148` | `¹²¹Sb` `I=7/2` `Q-Echo-8` ve `SU(8)` GRAPE | `6/7 PASS, 1/7 FAIL` | `SQ4 FAIL` (Cywiński `1/f`); `OQ6` model uzayında giderildi: statik Gross `0,5800 → 0,99908` (`455,5×`), `SU(8) ≥ 0,9954` | [`summary_exp148.md`](results/exp148_sb121_quadrupole_echo_qudit/summary_exp148.md) · [`test_exp148.py`](tests/test_exp148.py) |
| `Exp149` | Gerçek-EDA doğrulamalı Verilog RTL ve HTML5 gezgin | `8/8 PASS` | `no_external_eda_sim=false`, `no_vendor_vivado_pnr=true`; `0` `/` bölücü, `verilator -Wall` `0` uyarı, `iverilog` `64/64` + `4`-ch `0 LSB` / `584` çevrim, `yosys` `xcup_top16` (`102.886` LUT, `1.584` DSP, `96` BRAM36) + `nextpnr-ecp5` vekili (`43,58 MHz`) + `80,3 KB` HTML5 gezgin | [`summary_exp149.md`](results/exp149_boed_verilog_rtl_and_interactive_twin/summary_exp149.md) · [`test_exp149.py`](tests/test_exp149.py) |
| `Exp150` | Ön emniyet taraması `FMEA/HAZOP` (sertifikasız `M0`) | `7/7 PASS` | `iec61508_certified=false`, `semi_s2_certified=false`, `25` FMEA `max RPN 280 → 42`, IEC 61508-6 `PFH`, `15`-durumlu `λ_DU×β` taraması, RK4 ODH (`60 m³ %20,57`; `≤15 m³` yasak), `12,0 kWh` LFP UPS (`202,8 dk @ %90 DoD`), `S7.SAFETY $145k` | [`summary_exp150.md`](results/exp150_industrial_safety_fmea_hazop/summary_exp150.md) · [`test_exp150.py`](tests/test_exp150.py) |
| `Exp151` | `v7.2` bütünleşik artefakt özeti (`39/39` `SHA-256`) | `8/8 PASS` | `39/39` dosya bütünlüğü `SHA-256` manifestosu + `1.392/1.392` Stage-2 `%100` `SHA-256`, Faz-1 `$5,39M` (`%4,66`) → Faz-2 `$5,69M` (`%5,22`), `620/620` çıplak `pytest` (`50` takip edilen suit) | [`summary_exp151.md`](results/exp151_v7_digital_twin/summary_exp151.md) · [`test_exp151.py`](tests/test_exp151.py) |

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

- **Çevrimdışı HTML5 Model Gezgini:** [`docs/digital_twin_interactive.html`](docs/digital_twin_interactive.html) (`80,3 KB` / `80.339` bayt, `5` sekme, `0` harici CDN/HTTP çağrısı; yerel tarayıcıda doğrudan açılır).
- **Gerçek-EDA Doğrulamalı Verilog RTL:** [`rtl/boed_fpga/README.md`](rtl/boed_fpga/README.md) ve [`rtl/machine_ctrl/README.md`](rtl/machine_ctrl/README.md) (`0` kombinasyonel `/` bölücü, `verilator 5.055 -Wall` `0` uyarı/hata, `iverilog 14.0 + vvp` `64/64` + `4`-ch `0 LSB` / `584` çevrim, `yosys 0.71` `xcup`/`xc7`/`ecp5`, `nextpnr-ecp5` vekili `boed_q16_core 43,58 MHz` & `fpga_top_carrier_wrap 79/205 TRELLIS_IO`; `no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`).
- **Gerçek `1% ²⁹Si` Örgü Banyosu BOED Kıyaslaması:** [`results/boed_real_bath_benchmark.json`](results/boed_real_bath_benchmark.json) (`45.214` elmas-kübik örgü konumu, `N = 260`, `%91,15` vs `%84,62` Uniform, `130,4 ms/aday`, `10,46×` prob / `26,29×` zaman hızlanması, dürüst `2 kHz` Fourier duvarı & `SNR ≤ 3` uçurumu).

### Yazılım Regresyon Testleri (`50` Takip Edilen Test Dosyası — Çıplak `pytest -q`: `620/620 PASS`)

Aşağıdaki komut yalnızca kod tutarlılığını, birim doğruluğunu, açık-kaynak EDA eş-doğrulamasını ve iç yeniden üretilebilirliği sınar; fiziksel laboratuvar doğrulaması değildir. `pyproject.toml` yapılandırmasıyla depodaki **`50` takip edilen test dosyası** (`35` v7.2 + `14` Stage-2 + `1` `test_qcell_legacy.py`) çıplak `pytest -q` çağrısında **`620 passed, 0 failed`** verir ve yeniden koşumda hiçbir takip edilen dosyayı değiştirmez.

```bash
git clone https://github.com/berkmec/Atom-Lithography.git
cd Atom-Lithography
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 50 takip edilen test dosyası -> 620/620 PASS (sıfır mutasyon):
LC_ALL=C OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 pytest -q
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

Aşağıdaki **`7/7` Ham Disk Dosyası `SHA-256`** özetleri diskteki ham dosya baytlarıyla (`sha256sum`) birebir eşleşir; JSON manifestoları için ayrıca kendi iç kanonik yük özetleri (`cert["sha256"]`, `sha256` anahtarı hariç) ayrı sütunda verilmiştir. Bunlar yalnızca değiştirilmezlik izleme özetleridir; bilimsel doğrulama veya sertifikasyon anlamı taşımaz.

| Artefakt | Kapsam | Ham Disk Dosyası `SHA-256` (`sha256sum`) | Kanonik Yük `cert["sha256"]` |
|---|---|---|---|
| [`v7_digital_twin_cert.json`](results/exp151_v7_digital_twin/v7_digital_twin_cert.json) | `v7.2` bütünleşik dosya-bütünlüğü manifestosu (`Exp151`, `39/39` dosya) | `ae1ede37fd8819f79bd7882abe3f1229431a1ba7ecd9280ae00571b4863113f5` | `1f046684d8e633d3f964ec7325d1ada0a8765acc500012b09b8ade75350e1c62` |
| [`digital_twin_interactive.html`](docs/digital_twin_interactive.html) | Çevrimdışı HTML5 model gezgini (`80.339` bayt, `5` sekme) | `a7f067a217eee774c9abda6b9603d85e37c54f8c2ae37a9f022607f64859a821` | *(ham dosya)* |
| [`boed_real_bath_benchmark.json`](results/boed_real_bath_benchmark.json) | Gerçek `1% ²⁹Si` elmas-kübik örgü banyosu BOED kıyaslaması (`N=260`) | `5ef83da01ffe635c362ec887a07f82ed043eaa03799403e3645e505551f055a8` | *(ham dosya)* |
| [`ibm_qpu_live_results.json`](results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json) | Bulut QPU proxy (`ibm_marrakesh`, `156Q`) ham sayım defteri | `02b7a19d1704662c6424e76f4971e21b04a98d48230a917c9682853b3ca1fc5a` | *(ham dosya)* |
| [`v6_digital_twin_cert.json`](results/exp146_v6_digital_twin/v6_digital_twin_cert.json) | Tarihsel `v6.0` dosya-bütünlüğü manifestosu (`Exp146`) | `c46134b6e284be7851d714ff879970638c827a78f618082d71e6fbfd09faf001` | `ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7` |
| [`v5_digital_twin_cert.json`](results/exp141_v5_digital_twin/v5_digital_twin_cert.json) | Tarihsel `v5.0` dosya-bütünlüğü manifestosu (`Exp141`) | `336394f48f320f27127134f1055c55d5d7cda18496cc7c0599055ac81f7be055` | `2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1` |
| [`v4_digital_twin_cert.json`](results/exp135_v4_digital_twin/v4_digital_twin_cert.json) | Tarihsel `v4.0` dosya-bütünlüğü manifestosu (`Exp135`) | `a8f723ab658942529d9ed245682618f6a3333d27a00d5c7bd17fce550907ef77` | `feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57` |

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
| **Yazılım, Simülasyon, Kontrol Yığını, Testler, HTML5 Gezgin ve Depo Metaverisi** (`src/machine_control/**/*.py`, `experiments/**/*.py` [`build_bom_detailed.py` hariç], `tests/**/*.py`, `docs/digital_twin_interactive.html`, `requirements.txt`, `.gitignore`, `NOTICE`) | **GNU AGPLv3 veya üstü** (`AGPL-3.0-or-later` — bulut/SaaS ağ etkileşimi dâhil) | [`LICENSES/AGPL-3.0-or-later.txt`](LICENSES/AGPL-3.0-or-later.txt) · [`LICENSE`](LICENSE) |
| **Çapraz-Alan Donanım/RTL Üreteçleri, Derleme ve Veri/Spec Köprüsü** (`hardware/**/*.py`, `research/**/*.py`, `src/board/detector_frontend.py`, `experiments/exp128_bom_sensitivity/build_bom_detailed.py`, `rtl/**/Makefile`, `hardware/parts_registry.json`, `hardware/icd/parts/S8.*.json`, `BOM*.csv`, `cad_verification.json`, `results/**/*.json`, `results/**/*.jsonl`) | **Çift-Copyleft Köprü** (`AGPL-3.0-or-later OR CERN-OHL-S-2.0` — her iki seçim de kapatılamaz copyleft; çapraz lisans kilitlenmesini önler) | [`LICENSES/AGPL-3.0-or-later.txt`](LICENSES/AGPL-3.0-or-later.txt) · [`LICENSES/CERN-OHL-S-2.0.txt`](LICENSES/CERN-OHL-S-2.0.txt) |
| **Fiziksel Donanım ve Silikon/FPGA Verilog RTL** (`**/*.v`, `**/*.sv`, `**/*.xdc`, `**/*.hex`, `**/*.mem`, `**/*.ys`, `**/*.stl`, `**/*.step`, `**/*.scad`, `**/*.dxf`, `**/*.svg`, `**/*.kicad_pcb`, `**/*.kicad_sch`, `**/*.kicad_pro`, `**/*.cir`, `**/*.net` ve donanım `*.json` dosyaları) | **CERN Open Hardware Licence v2 — Strongly Reciprocal** (`CERN-OHL-S-2.0`, Bölüm 8.3 uyarınca v2 veya üstü `S` varyantı — PCB/CAD + FPGA/ASIC üretimi dâhil) | [`LICENSES/CERN-OHL-S-2.0.txt`](LICENSES/CERN-OHL-S-2.0.txt) |
| **Dokümantasyon, Bilimsel Raporlar ve Şekiller** (`**/*.md`, `**/*.png`) | **Creative Commons Attribution-ShareAlike 4.0** (`CC-BY-SA-4.0`) | [`LICENSES/CC-BY-SA-4.0.txt`](LICENSES/CC-BY-SA-4.0.txt) |

Tüm materyaller ilgili lisans metinlerinde belirtildiği biçimde **"OLDUĞU GİBİ" (*AS IS*)** sunulur; donanım tasarımları `M0/M1 DESIGN_ONLY` aşamasındadır ve fonksiyonel emniyet sertifikası taşımaz. `berkmec` ve `https://counfield.com/` ad/alan adları için ticari onay veya marka hakkı devri verilmez.
