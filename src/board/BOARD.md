# Devre Kartı Tasarımı — 8-Kanallı IBIC Algılayıcı Ön Ucu (v2.1 / Exp127 `COLD_100K` Kilidi)

Kapsam: BOM `S3.1/S3.2/S3.3` + `S2.4` FPGA sayım arayüzü (`DESIGN.md v3.0`, `Exp72`, `Exp91`, `Exp127`).
**Epistemik durum: `{Model}` & `{Aday-COTS}` — yerleşim öncesi (pre-layout) elektrik tasarımı; KiCad `.kicad_pcb`/Gerber yerleşimi ve fiziksel laboratuvar ölçümü yoktur.**

## 1. Artefaktlar, Kilitli Varsayılan Profil & ERC Doğrulaması
- `detector_frontend.py` — 8-kanallı tam elektrik grafı, KiCad netlist üreticisi, SPICE deste üreticisi ve otomatik **ERC doğrulayıcısı** (`validate_netlist()`).
  - **Varsayılan kilitli profil (`--profile cold100k`, Exp127 `F3` kapanışı):** `T = 100 K` soğuk-ada CSA, **`RF = 1 GΩ`** (`τ_f = 250 µs`), **`CS = CP = 600 pF`**, `RS1 = RS2 = 2,00 kΩ` (**`τ_s = 1,2 µs`**), **`Q_ION = 0,055 fC`** (`~342 e⁻` Lindhard `5 keV ³¹P⁺ @ 100 K`), **`V_THR = 4,23 mV`** (`5,5σ_ENC`).
  - İsteğe bağlı sıcak profil (`--profile rt300k`): `300 K / 200 ns` (`RF = 100 MΩ`, `CS = CP = 100 pF`, `Q_ION = 0,056 fC`, `V_THR = 15,67 mV`; `5 keV` Lindhard altında `η = 0,0972` ile yetersizdir).
- `detector_frontend.net` — Geçerli KiCad (version D) S-ifadesi netlist (**`COLD_100K` kilitli: 204 bileşen, 107 benzersiz net, 0 ERC hatası**; 0 boşta pin, 0 pin-net çakışması, 0 jenerik yer tutucu).
- `detector_frontend.cir` — Standart SPICE3/ngspice makro-model destesi (`Profile=COLD_100K`, `R_F=1G`, `C_S=C_P=600p`, `Q_ION=0.055f`, `V_THR=0.00423`, `.subckt IBIC_CHANNEL`, `OPAMP_LTC6268`, `OPAMP_ADA4817`, `CMP_TLV3501`, 8 kanal + `.ac`/`.tran`/`.noise`).
- FPGA tarafı: `../rtl/blanker_gate.v` & `../rtl/blanker_tile.v` (`100 MHz`; `16×` 64-kanallı karo = `1.024` `Arch-B` demetcik).

## 2. Kanal Mimarisi & Aday Bileşenler (`CH0..CH7`, Kilitli `COLD_100K`)

| Kat | Bileşen | Aday Parça & Etiket | Değerler / İşlev (`COLD_100K` Kilitli) |
|---|---|---|---|
| HV Bias Filtresi | `RBIAS_BULK/CBIAS_BULK`, `RBIAS{ch}/CBIAS{ch}` | `{Pasif-COTS}` | `-30 V` ortak besleme → `100 kΩ/100 nF` + kanal başı `10 MΩ/10 nF` |
| Piksel Diyot | `D0..D7` | `IBIC_PIXEL_DIODE_C0p5` `{Özel-Üretim}` | `C_det ≤ 0,5 pF` koruma halkalı Si p-i-n piksel diyot (`η ≥ 0,99` penceresi `C_det ≤ 1,5 pF`) |
| CSA (İlk Kademe, `100 K`) | `U0A..U7A`, `CF`, `RF` | **`LTC6268`** `{Aday-COTS}` | Birim-kazanç kararlı FET op-amp (`GBP=500 MHz`, `C_in=0,45 pF`, `±2,5 V`); `Cf=0,25 pF`, **`Rf=1 GΩ`** (`1G_THICKFILM`, `τ_f=250 µs`); `IN+ = AGND` |
| CR-RC Aktif Şekillendirici | `CS`, `RS1`, `U0B..U7B`, `RG1/RG2`, `RS2`, `CP` | **`ADA4817-1`** `{Aday-COTS}` | `GBP=1,05 GHz`; **`CS=CP=600 pF`** (`600pF_C0G_1pct`), `RS1=RS2=2,00 kΩ` (**`τ_s = 1,2 µs`** `≪ 15 ms` atış); `RG1=100 Ω`, `RG2=13,5 kΩ` (`G_stage=136 →` balistik `1/e` sonrası net tepe kazancı `×50,0`) |
| Kanal-Başı Eşik DAC | `UDAC`, `RDAC`, `CDAC` | **`DAC8568`** `{Aday-COTS}` | 8-kanallı 16-bit SPI DAC + kanal başı `1 kΩ / 100 nF` RC filtre (`f_c=1,59 kHz`); yükselen kenar `V_DAC = V_thr − 0,5·V_hys` |
| Histerezisli Karşılaştırıcı | `U0C..U7C`, `RHYS1/2`, `RTERM` | **`TLV3501`** `{Aday-COTS}` | `t_pd = 4,5 ns`, `+3,3 V` CMOS; `RHYS1=1 kΩ, RHYS2=1 MΩ` (`3,3 mV` histerezis); `49,9 Ω` seri sonlandırma → `JFPGA` `COUNT_HIT[0:7]` |
| Güç & Yıldız Toprak | `JPWR`, `R_STAR`, `CBULK*`, `CD*` | `{Pasif-COTS}` | `VCCA (+2,5 V)`, `VSSA (−2,5 V)`, `VCCD (+3,3 V)`, `AGND ↔ DGND` (`R_STAR = 0 Ω`), her aktif IC'de `100 nF C0G` dekuplaj |

## 3. Exp127 Birinci-İlkeler Sinyal, Gürültü & Verim Bütçesi

- **Lindhard Sinyali (Exp72'den ~%28 daha sert):** `5 keV P91` → **`341,7 e⁻` (`0,0548 fC`) @ 100 K** (`351,2 e⁻` @ 300 K); `10 keV` → `770,8 e⁻` @ 100 K (`792,0 e⁻` @ 300 K).
- **Laplace / ODE Doğrulaması:** `1111 e⁻` darbesinde FFT tepesi `35,200 mV` vs `scipy.signal.impulse` `35,201 mV` (`%0,004` fark; `t_peak = 224,7 ns` @ `200 ns` profil, `1218 ns` @ `1,2 µs` kilitli profil).
- **Rice Yanlış-Tetik Sınırı:** `5,5σ` yükselen kenar eşiği (`4,23 mV` @ `COLD_100K`) **`P_false = 2,59×10⁻⁴ / 1 ms` (`< 10⁻³`)** sağlar.
- **Kilitli `COLD_100K` vs. İsteğe Bağlı `RT_300K` (`C_det = 0,5 pF`, `50.000` İyon MC):**
  1. **Kilitli `COLD_100K` (`100 K / 1,2 µs / Rf=1 GΩ`, varsayılan netlist/SPICE):** **`ENC = 24,1 e⁻ rms`**, **`η(5 keV P91) = 0,99936`**, **`η(10 keV) = 1,00000`**, **`η ≥ 0,99` penceresi `C_det ≤ 1,5 pF`** (`3×` kapasitans marjı; `1,2 µs` şekillendirme `15 ms` HDA-HiRes atış çevriminin `< %0,01`'idir).
  2. **İsteğe bağlı `RT_300K` (`--profile rt300k`, `300 K / 200 ns / Rf=100 MΩ`):** `ENC = 89,9 e⁻ rms` → `10 keV η = 0,9774`, **`5 keV η = 0,0972` (P91 5 keV için YETERSİZ)**.

## 4. Doğrulanmış Olan / Olmayan
- **Doğrulanan (`{Model}` / `{EDA}`):** KiCad/SPICE `COLD_100K` & `RT_300K` ERC (`0` hata, `pytest tests/test_detector_frontend.py` PASS), Laplace↔ODE transfer fonksiyonu (`%0,004`), Parseval ENC ve 50k-iyon MC verimi (`Exp127`), RTL `blanker_gate`/`blanker_tile` BMC+indüksiyon.
- **Açık (dış altyapı / M1-M2 gerekir):** KiCad 4-katmanlı PCB yerleşimi & guard-ring parazitik çıkarımı (`C_par ≤ 0,25 pF`), ngspice transistör-düzeyi 100 K köşe simülasyonu, kriyo-termal döngü ve gerçek `5 keV ³¹P⁺` IBIC kalibrasyonu.
