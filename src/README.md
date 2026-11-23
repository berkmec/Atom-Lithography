# Atom Litografi Makinesi — Yazılım, `BOED`, `CellISA v3.0` Derleyici & Devre Paketi (`v3.0`)

Tasarım: `research/atom_lithography_machine/DESIGN.md v4.0` (`Exp124–Exp135` tam senkronu).
**Epistemik sınır:** Fiziksel donanım, üretilmiş PCB, laboratuvar ölçümü veya silikon tape-out yoktur (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`); tüm yığın doğrulanmış `{Model}` / `{EDA}` katmanıdır.

## İçerik

### 1. `src/machine_control/` (`v3.0`) — Fabrika Kontrolü, `BOED` & `CellISA v3.0` Programlama Yığını
`yaz → algıla → flaş tavlama → BOED uyarlamalı ölç → seç → kalibre et → derle/doğrula` tam akışı:
- `config.py`: Geriye uyumlu `MachineConfig` + açık önayarlar:
  - **`MachineConfig.v400_bayesian()` (`--preset v400`):** `v4.0` kilitli baz noktası — `BOED` 3-aşamalı uyarlamalı spektroskopi (`41,03 ms/yuva`, `$0` ek HW, `1,502–2,253×10⁹` yazmaç/gün), `S5.5` flaş-tavlama sağkalımı, `S6.9` `PT420` dekuplajı ve `CellISA v3.0`.
  - `MachineConfig.v300_baseline()` & `MachineConfig.v224_baseline()` — `v3.0` kilitli `Arch-B` eş-adımlı dizi **`1.024` demetcik** (`32×32 @ 0,50 mm = 16,0×16,0 mm`, köşegen `22,63 mm < Ø28,0 mm`, `16×` 64-kanallı karo), `Exp124 HDA-HiRes` `5 keV P91` `shot_cycle_s = 0,015 s`, `Exp127` soğuk `100 K` IBIC `detector_eta = 0,9994`, `NL=160 × 56` zincir (`8960` okuma kanalı), `S6.8=D` (`MXC 20 mK`), `B_örnek=1,5 T`, `f=%1` Mod B, çift-`α` (`α=1 ∧ α=2`) DD kapısı.
  - `MachineConfig.v224_1k_upgrade()` — `Exp117/118` `1 K` PSB alternatifi (`S6.8=C`, `3,165×` ortalama süresi).
  - `MachineConfig.legacy_exp65()` — `2026-10-20` `Exp65–72` baz noktası (geriye uyumlu).
- **`adaptive_spectroscopy.py` (`Exp132`, `$0` ek HW):** 3-aşamalı Bayesci optimal deney tasarımı (`BayesianSpectroscopy`) — ortalama spektroskopi süresini `1.000 ms → 41,03 ms` (`24,37×` ham hızlanma), frekans hatasını `RMS = 72,67 Hz` (`CRLB = 58,19 Hz`), `FNR = %0,20`, `FPR = %0,00` düzeyine indirir.
- `selector.py`: `StochasticSelector` (hızlı) ve taşınabilir **Linux-uyumlu `AtlasSelector`** (arşivdeki `Exp42/43/44/48` dosyalarına dokunmadan bellek-içi yol köprüsüyle gerçek darbe-duyarlı seçim makinesini çalıştırır).
- `pulse_engine.py`: Gerçek `³¹P + ²⁹Si` aşırı-ince Hamiltonyen (`SU(2)` Rodrigues + `2^(N+1)` çok-spin Hilbert uzayı), 9-köşeli (`±400 Hz × ±2%`) L-BFGS-B **GRAPE** darbe sentezi ve Ornstein–Uhlenbeck banyo gürültüsü altında **XY8 dinamik ayrıştırma (`DD_HOLD`)** motoru. *(Soyutlama sınırı `F7`: `MultiSpinSimulator.apply_dd_hold` hızlı derleme için efektif koherens faz operatörü `0.5*acos(dd_coherence)` uygular; tam 32B `448`-seyirci `XY8-GRAPE` doğrulaması `experiments/exp126_atom_cell_programming/` içindedir.)*
- `calibrator.py`: `mode="spectral"` (hızlı 5 kHz kapısı) + `mode="shaped"` / `mode="grape"` canlı 9-köşe darbe sentezi ve doğrulaması.
- **`programmer.py` (`CellISA v3.0` — `14` Komut & `MultiCellProgrammer`):** 10 temel komut (`INIT`, `RX`, `RY`, `RZ`, `CZ`, `CNOT`, `GHZ`, `DD_HOLD`, `MEASURE`, `ARRAY_EXEC`) + `v3.0` yonga/veri-yolu/mantıksal komutları (**`WAFER_MAP_ROUTE`**, **`BUS_TUNE`**, **`BUS_CZ`**, **`LOGICAL_ENCODE`**), `AtomCellProgrammer`, `MultiCellProgrammer` (`4×4` Kraus `F_joint = 0,983448`, `min_bus_cz = 0,988923`, `p_L = 3,65×10⁻⁴`) ve **SHA-256 imzalı `ProgramCertificate`** (JSONL).
- `factory.py` & `sim.py`: CLI:
  ```bash
  PYTHONPATH=src python3 -B -m machine_control.sim \
      --slots 4000 --preset v400 --program ghz --program-mode grape \
      --certs results/exp127_detector_frontend_sim/certs_v224_demo.jsonl
  ```

### 2. `src/board/` (v2.1 / Exp127 `COLD_100K` Kilidi) — 8-Kanallı IBIC Ön-Uç Devresi
- `detector_frontend.py` → Varsayılan kilitli **`COLD_100K`** profili (`RF = 1 GΩ`, `CS = CP = 600 pF → τ_s = 1,2 µs`, `Q_ION = 0,055 fC`, `V_THR = 4,23 mV`; isteğe bağlı `--profile rt300k`) ile ERC-doğrulamalı (`0` hata) `detector_frontend.net` (KiCad vD, **204 bileşen, 107 net**) ve `detector_frontend.cir` (SPICE3/ngspice destesi): `LTC6268` CSA + `ADA4817-1` tamponlu CR-RC şekillendirici (`×50` net tepe) + `DAC8568` 8-kanallı SPI eşik DAC + `TLV3501` histerezisli karşılaştırıcı (`{Aday-COTS}`).
- Tam fiziksel Lindhard/Laplace/Parseval/MC analizi: `experiments/exp127_detector_frontend_sim/` & `src/board/BOARD.md`.

### 3. `src/rtl/` — Sayılmış-İmplantasyon Blanker Çekirdeği & Karosu
- `blanker_gate.v` (tek kanal, BMC kanıtlı) ve `blanker_tile.v` (64 kanal, zamansal tümevarım + Yosys TT sentezi `117.541 µm² / 11.835 hücre`; `1.024` `Arch-B` demetcik = `16` karo).

### 4. Yerel Arşiv Notu (`src/qcell/`)
- Erken `Exp0–Exp22 / Exp32` faz-alanı / FEM / MOS / `4 K` kompakt model kütüphanesi (`src/qcell/`) yalnızca yerel arşivde tutulur; Atom Litografi Makinesi çekirdeği tarafından içe aktarılmaz ve GitHub yayın paketinde yer almaz.

## Testler & Doğrulama (2026-11-23)
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B -m pytest -p no:cacheprovider \
    tests/test_machine_control.py tests/test_atom_programmer.py tests/test_exp132.py \
    tests/test_exp135.py tests/test_detector_frontend.py tests/test_rtl_contract.py \
    tests/test_blanker_tile.py
```
- **Makine yazılımı (`BOED` + `CellISA v3.0`) + Dijital İkiz + IBIC ön-uç + RTL sözleşme testleri:** **`47/47 PASS`** (`test_machine_control.py` 12, `test_atom_programmer.py` 11, `test_exp132.py` 6, `test_exp135.py` 6, `test_detector_frontend.py` 6, `test_rtl_contract.py` 3, `test_blanker_tile.py` 3); tüm **`17/17`** Atom Litografi test paketi **`142/142 PASS`**.
