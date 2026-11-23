# Atom Litografi Makinesi — Yazılım, `Q16.16` FPGA Verilog RTL, İnteraktif Dijital İkiz, `CellISA v4.0`, Canlı IBM QPU Köprüsü & Devre Paketi (`v7.0`)

Tasarım: `research/atom_lithography_machine/DESIGN.md v7.0` (`Exp124–Exp151` tam senkronu).

> **Epistemik Sınır (Kristal Ayrım):**
> - **Silikon `³¹P/¹²¹Sb/¹⁶⁷Er` fabrikasyon, `M1–M4` makine fiziği, `rtl/boed_fpga/` Verilog RTL sentezi (`no_external_eda_sim=true`), `Exp150` emniyet & `auto_recal.py` simülasyonu:** `M0` tasarım & sayısal fizibilite (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).
> - **Kontrol yığını (`CellISA v4.0 → OpenQASM 3.0`), `Echo/XY4` DD, `d=3` sendrom dekoderi ve bit-kesin `Q16.16` BOED:** **Gerçek `156`-kübitlik `ibm_marrakesh` (IBM Heron r2, `job_id = dc1tdo2nj2vs73dfrfl0`, `16 PUB × 4.096 shot`, `32,54 s`) süperiletken bulut QPU üzerinde canlı doğrulandı** (`{Canlı-Donanım-IBM-QPU}`, sıfır gizli anahtar sızıntısı).

## İçerik

### 1. `src/machine_control/` (`v4.0`) — Fabrika Kontrolü, `Q16.16` FPGA, `CellISA v4.0`, IBM QPU & Otonom Kurtarma
`yaz → algıla → 1530,1 K flaş + S5.6 MBE → BOED / Q16.16 FPGA ölç → seç → kalibre et → CellISA v4.0 (qLDPC / qRAM / OpenQASM 3.0) yürütme → auto_recal` tam akışı:
- `config.py`: Geriye uyumlu `MachineConfig` + açık önayarlar:
  - **`MachineConfig.v400_bayesian()` (`--preset v400`):** `BOED` 3-aşamalı uyarlamalı spektroskopi (`41,03 ms/yuva`, `$0` ek HW, `1,502–2,253×10⁹` yazmaç/gün), `S5.5` flaş-tavlama sağkalımı, `S6.9` `PT420` dekuplajı ve `CellISA v4.0`.
  - `MachineConfig.v300_baseline()` & `MachineConfig.v224_baseline()` — Kilitli `Arch-B` eş-adımlı dizi **`1.024` demetcik** (`32×32 @ 0,50 mm = 16,0×16,0 mm`, köşegen `22,63 mm < Ø28,0 mm`, `16×` 64-kanallı karo), `Exp124 HDA-HiRes` `5 keV P91` `shot_cycle_s = 0,015 s`, `Exp127` soğuk `100 K` IBIC `detector_eta = 0,9994`, `NL=160 × 56` zincir (`8960` okuma kanalı), `S6.8=D` (`MXC 20 mK`), `B_örnek=1,5 T`, `f=%1` Mod B, çift-`α` (`α=1 ∧ α=2`) DD kapısı.
  - `MachineConfig.v224_1k_upgrade()` — `Exp117/118` `1 K` PSB alternatifi (`S6.8=C`, `3,165×` ortalama süresi).
  - `MachineConfig.legacy_exp65()` — `2026-10-20` `Exp65–72` baz noktası (geriye uyumlu).
- **`adaptive_spectroscopy.py` (`Exp132`, `$0` ek HW):** 3-aşamalı Bayesci optimal deney tasarımı (`BayesianSpectroscopy`) — ortalama spektroskopi süresini `1.000 ms → 41,03 ms` (`24,37×` ham hızlanma), frekans hatasını `RMS = 72,67 Hz` (`CRLB = 58,19 Hz`), `FNR = %0,20`, `FPR = %0,00` düzeyine indirir.
- **`fpga_boed_dsp.py` (`Exp140` — `Q16.16` Sabit-Nokta RFSoC FPGA Motoru):** `ZCU216` (`XCZU49DR`, `250 MHz`) için bit-kesin `Q16.16` sabit-nokta BOED DSP motoru — FP64'e karşı **`abs(ΔRMS) = 0,0502 Hz`** (`Exp141` canlı ikiz: `0,0183 Hz`; canlı **`ibm_marrakesh` `3`-nokta Ramsey `120,11 kHz`**, FP64'ten **`1,6 Hz`** fark!), döngü-kesin gecikme **`2,336 µs/adım`**, kaynak kullanımı **`%10,49` DSP48E2** (`N_mux* = 32` okuma çoklamasıyla tam senkron).
- **`programmer.py` (`CellISA v4.0` — `20` Komut & `MultiCellProgrammer`):** 10 temel `v2.0` (`INIT`, `RX`, `RY`, `RZ`, `CZ`, `CNOT`, `GHZ`, `DD_HOLD`, `MEASURE`, `ARRAY_EXEC`) + 4 `v3.0` (`WAFER_MAP_ROUTE`, `BUS_TUNE`, `BUS_CZ`, `LOGICAL_ENCODE`) + 3 `v3.5` (`ECHO_CZ`, `MUX_READOUT`, `SYNDROME_CYCLE` — donmuş `VALID_OPCODES` = `17` geriye uyumlu) + **3 yeni `v4.0` komutu (`VALID_OPCODES_ALL` = `20`: `QRAM_SWAP`, `QLDPC_ROUND`, `AUTO_RECAL`)**, `AtomCellProgrammer`, `MultiCellProgrammer` (`execute_qram_swap` `F=0,999893`, `execute_qldpc_round` `[[144,12,12]]`, `execute_auto_recal`, canlı `v3.5` `ECHO_CZ = 0,9818`, `F_syn = 0,9427`, `T_cyc = 2,620 µs`) ve **SHA-256 imzalı `ProgramCertificate`** (JSONL).
- **`cloud_qpu_bridge.py` (`Exp145` — Sıfır-`qiskit` Saf-`requests` IBM Quantum Platform 2026 Köprüsü):** IBM Cloud IAM + bölgesel CRN otomatik algılama + `16-dt` hizalı native-ISA `OpenQASM 3.0` derleyicisi (`Heron cz` & `Eagle ecr`) + Heavy-Hex `0`-SWAP küresel-optimal 5-kübit doğrusal zincir seçici (`select_best_linear_chain`) + evrensel `SamplerV2` çözücü (`parse_sampler_v2_counts`). Gerçek **`ibm_marrakesh` (`156Q`, `dc1tdo2nj2vs73dfrfl0`)** üzerinde canlı doğrulandı: Bare `0,3325` → Echo `0,9224` (`+59,0 pp`) → XY4 `0,9280` (`+59,5 pp`), Bell `0,9733`, `d=3` MWPM `5,16×` / maj `7,83×` / postsel `%0,00`, `Q16.16 BOED` `120,11 kHz` (`1,6 Hz` vs FP64).
- **`auto_recal.py` (`Exp145` — Otonom Kendini-Onaran Kapalı Çevrim Kontrolör):** `CellISA v4.0` `AUTO_RECAL` işlem kodunu 4 kritik arıza kipinde (1: `S5.5` `±%8` lazer güç kayması → `σ_anneal ≤ 0,50 nm`; 2: `S5` UHV basınç sıçraması → `< 1 ms` blanker kilidi; 3: `S3` `%5` ölü blanker kanalı → `128` yedek halka yeniden eşleme; 4: `³¹P` `±350 Hz` termal frekans kayması → `< 5 ms` `Q16.16` BOED yeniden kilitleme) **`4/4 PASS`** olarak doğrular (`{Model}`).
- `selector.py`: `StochasticSelector` (hızlı) ve taşınabilir **Linux-uyumlu `AtlasSelector`** (arşivdeki `Exp42/43/44/48` dosyalarına dokunmadan bellek-içi yol köprüsüyle gerçek darbe-duyarlı seçim makinesini çalıştırır).
- `pulse_engine.py`: Gerçek `³¹P + ²⁹Si` aşırı-ince Hamiltonyen (`SU(2)` Rodrigues + `2^(N+1)` çok-spin Hilbert uzayı), 9-köşeli (`±400 Hz × ±2%`) L-BFGS-B **GRAPE** darbe sentezi ve Ornstein–Uhlenbeck banyo gürültüsü altında **XY8 dinamik ayrıştırma (`DD_HOLD`)** motoru. *(Soyutlama sınırı `F7`: `MultiSpinSimulator.apply_dd_hold` hızlı derleme için efektif koherens faz operatörü `0.5*acos(dd_coherence)` uygular; tam 32B `448`-seyirci `XY8-GRAPE` doğrulaması `experiments/exp126_atom_cell_programming/` içindedir.)*
- `calibrator.py`: `mode="spectral"` (hızlı 5 kHz kapısı) + `mode="shaped"` / `mode="grape"` canlı 9-köşe darbe sentezi ve doğrulaması.
- `factory.py` & `sim.py`: CLI:
  ```bash
  PYTHONPATH=src python3 -B -m machine_control.sim \
      --slots 4000 --preset v400 --program ghz --program-mode grape \
      --certs results/exp127_detector_frontend_sim/certs_v224_demo.jsonl
  ```

### 2. `src/board/` (v2.1 / Exp127 `COLD_100K` Kilidi) — 8-Kanallı IBIC Ön-Uç Devresi
- `detector_frontend.py` → Varsayılan kilitli **`COLD_100K`** profili (`RF = 1 GΩ`, `CS = CP = 600 pF → τ_s = 1,2 µs`, `Q_ION = 0,055 fC`, `V_THR = 4,23 mV`; isteğe bağlı `--profile rt300k`) ile ERC-doğrulamalı (`0` hata) `detector_frontend.net` (KiCad vD, **204 bileşen, 107 net**) ve `detector_frontend.cir` (SPICE3/ngspice destesi): `LTC6268` CSA + `ADA4817-1` tamponlu CR-RC şekillendirici (`×50` net tepe) + `DAC8568` 8-kanallı SPI eşik DAC + `TLV3501` histerezisli karşılaştırıcı (`{Aday-COTS}`).
- Tam fiziksel Lindhard/Laplace/Parseval/MC analizi: `experiments/exp127_detector_frontend_sim/` & `src/board/BOARD.md`.

### 3. `src/rtl/` & `rtl/boed_fpga/` (`v7.0` / `Exp149`) — Blanker Karosu & Sentezlenebilir `Q16.16` BOED-FPGA Verilog RTL
- `src/rtl/`: `blanker_gate.v` (tek kanal, BMC kanıtlı) ve `blanker_tile.v` (64 kanal, zamansal tümevarım + Yosys TT sentezi `117.541 µm² / 11.835 hücre`; `1.024` `Arch-B` demetcik = `16` karo).
- **`rtl/boed_fpga/` (`Exp149`, `10` dosya, `no_external_eda_sim=true`):** `fpga_boed_dsp.py` sabit-nokta motorunun **sentezlenebilir IEEE 1364-2005 Verilog RTL** gerçeklemesi (`boed_lut_rom.v`, `boed_isqrt_cordic.v`, `boed_q16_core.v`, `boed_top_16ch.v` — toplam **`894` satır**, `0` sentez/port/genişlik hatası; `rom_loglik_p0/p1.hex` `1.024/1.024` `0`-bit fark; `golden_vectors.mem` **`64/64` `0 LSB`** + `1.000` `isqrt` `0 LSB`; kesin **`584` çevrim = `2,336 µs @ 250 MHz`**, `4` çevrim SPRT; `zu48dr_boed_250mhz.xdc` + `tb_boed_q16_core.v` + [`rtl/boed_fpga/README.md`](../rtl/boed_fpga/README.md); `ZU48DR` `16` kanal `%10,49` DSP48E2, `%5,93` BRAM36, `0 W` kriyo).
- **Canlı İnteraktif HTML5 Dijital İkiz (`docs/digital_twin_interactive.html`, `Exp149/Exp151`):** `66,6 KB` (`66.554` bayt), `5` sekme, `0` harici CDN/HTTP, `0` sızıntı — doğrudan diskteki birincil JSON'lardan derlenen etkileşimli tarayıcı ikizi (`SHA-256 = f9f45721c7dd67fe06616a29e3d98b72e10ded75221293ee5efbf15cefca2bc0`).

### 4. Yerel Arşiv Notu (`src/qcell/`)
- Erken `Exp0–Exp22 / Exp32` faz-alanı / FEM / MOS / `4 K` kompakt model kütüphanesi (`src/qcell/`) yalnızca yerel arşivde tutulur; Atom Litografi Makinesi çekirdeği tarafından içe aktarılmaz ve GitHub yayın paketinde yer almaz.

## Testler & Doğrulama (2026-11-23, `v7.0`)
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src python3 -B -m pytest -p no:cacheprovider \
    tests/test_machine_control.py tests/test_atom_programmer.py tests/test_exp132.py \
    tests/test_exp135.py tests/test_exp140.py tests/test_exp141.py \
    tests/test_exp145.py tests/test_exp146.py tests/test_exp149.py tests/test_exp151.py \
    tests/test_detector_frontend.py tests/test_rtl_contract.py tests/test_blanker_tile.py
```
- **Makine yazılımı (`BOED` + `Q16.16` FPGA + `CellISA v4.0` + `ibm_marrakesh` QPU köprüsü + `auto_recal`) + Verilog RTL & İnteraktif İkiz (`Exp149`) + Dijital İkizler (`v4`/`v5`/`v6`/`v7`) + IBIC ön-uç + RTL sözleşme testleri (`13` dosya):** **`108/108 PASS`** (`test_machine_control.py` `12`, `test_atom_programmer.py` `11`, `test_exp132.py` `6`, `test_exp135.py` `6`, `test_exp140.py` `7`, `test_exp141.py` `9`, `test_exp145.py` `12`, `test_exp146.py` `10`, `test_exp149.py` `10`, `test_exp151.py` `13`, `test_detector_frontend.py` `6`, `test_rtl_contract.py` `3`, `test_blanker_tile.py` `3`); tüm **`33/33`** staged Atom Litografi test paketi **`306/306 PASS`**.
