# IBIC Cryo Front-End v3 — Split 3-PCB KiCad 8 Kit & Real 100 K `ngspice` Verification

**BOM Coverage:** `S3.1-01`, `S3.1-02`, `S3.2-01`, `S3.2-02`, `S3.2-03`, `S3.2-04`, `S3.2-05`, `S3.2-06`, `S3.3-03`  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. All active semiconductors are `{Aday-COTS}` candidate parts.

## 1. Physically Split 3-PCB Kit (100% Physically Routed Pad-to-Pad; Closing #281 & #327)

Replaces the pre-layout monolithic netlist (`src/board/detector_frontend.*`, preserved read-only for v7.2 hash parity) with 3 physically split KiCad 8 boards verified by strict S-expression parsing, reconstructive schematic-to-PCB ERC, full geometric + pad-segment-via-zone Union-Find connectivity DRC (`0` unconnected items, `0` dangling tracks), controlled-impedance `Z0` (`±5%`), IPC-2221/IEC-61010 HV rules, real `ngspice-47`, and independent Python MNA:

| Board Slug | BOM IDs | Temp / Env | Stackup & Size | Comps / Nets | Routed / Unconn / Dangling | Segs / Vias | ERC / DRC | Key Features |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `ibic_cold_csa_100k` | `S3.2-01, S3.1-01/02, S3.2-04/05` | `100 K` UHV (`10⁻⁹ mbar`) | 4L Rogers RO4350B (`ε_r=3.48`), `125×105 mm` | `130 / 56` | **`56/56` / `0` / `0`** | `725 / 225` | **`0 / 0`** | 8× `LTC6268IS8` CSA (exact S8 pinout: `1:~SHDN, 2:V+, 3:OUT, 4:V-, 5/8:GUARD_DRV, 6:-IN, 7:+IN`) + `0805` cryo thin-film `1 GΩ` `RF`, extended `In1/In2` keepouts (`x=34.0..55.2 mm`) & active `U_GRD_BOOT` guard follower (no `100 nF` AC-short), `G=+2` `50 Ω` coax drivers (`Z0=50.00 Ω`) |
| `ibic_warm_shaper_300k` | `S3.2-02, S3.2-06, S3.3-03` | `300 K` EMI Chassis | 4L Isola FR408HR (`ε_r=3.66`), `185×135 mm` | `217 / 116` | **`116/116` / `0` / `0`** | `1,373 / 350` | **`0 / 0`** | 16× `ADA4817-1ARDZ` (`SOIC-8-1EP`: `1:FB, 8:PD=VCCA, 9:EP=VSSA`), 8× `TLV3501AIDBVR` (exact TI SBOS321 DBV: `1:-IN, 2:V-, 3:+IN, 4:V+, 5:OUT, 6:SHDN=DGND`), 5× `MSOP-12-1EP` `LT3045EMSE` (`EP=GND`) / `LT3094EMSE` (`EP=VIN_N`), 100% `F.Cu` `50 Ω` `SHP_ADC`/`COUNT_HIT`/`COAX_IN` over solid `In1.Cu` `AGND`/`DGND` (`0` `B.Cu` `50 Ω` segments) |
| `ibic_hv_bias_guard` | `S3.2-03, S3.1-01/02` | `300 K` HV / Guard | 4L Rogers RO4350B (`ε_r=3.48`), `110×75 mm` | `38 / 21` | **`21/21` / `0` / `0`** | `170 / 32` | **`0 / 0`** | 3-stage RC `0–100 V` HV filter (`3× 10 kΩ / 1.0 µF` 200 V), extended `2.5×61 mm` milled `Edge.Cuts` air-slot enclosing `RHV_DIV_TOP`, non-chopper `AD8675ARZ` driven guard buffer + `100:1` HV sense monitor |

## 2. Real `ngspice-47` & Independent MNA Verification (`ibic_cryo_chain_100k.cir`)

Executed natively with `ngspice-47 -b` (zero PSpice `VALUE={}` / `PARAMS:` syntax, exit code `0`, `0` errors, `0` warnings) using `.temp -173.15` (`100 K`) on the cold CSA stage (with active guard bootstrap follower, `0805` thin-film `RF` parasitic C, and `±2.5 V` supply-rail saturation clamps) and per-resistor `temp=26.85` (`300 K`) on the warm ex-vacuum shaper & HV filter:

| Metric | `ngspice-47` Measured | Independent Python MNA / Exp127 Ref | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| Peak AC Transimpedance `Z_peak` | `647.44 MΩ` (`@ 7.34 kHz`) | MNA `647.44 MΩ` (`0.0001%` diff) | `< 1%` MNA parity | **PASS** |
| `5 keV ³¹P⁺` Shaper Peak `V_peak` (`341.7 e⁻`) | `10.834 mV` (`197.9 mV/fC`) | Exp127 `10.917 mV` | `10–12 mV` | **PASS** |
| `5 keV` Peaking Time `t_peak` | `1225.6 ns` (`1.226 µs`) | Exp127 `1218.4 ns` | `≈ 1.2 µs` | **PASS** |
| Buffered FMC PHA ADC Tap `V_adc` | `10.780 mV` | `0.50%` tracking vs `V_peak` | `< 2%` tracking | **PASS** |
| Integrated Noise `ENC` (`10 Hz – 50 MHz`) | **`27.94 e⁻ rms`** | Active guard bootstrap + `300 K` warm shaper & `50 Ω` coax link | `≤ 35 e⁻` | **PASS** |
| `TLV3501` Comparator `COUNT_HIT` | `3.251 V`, `5.20 µs` pulse (`0 V` DC baseline, `SHDN=DGND`) | `V_thr = 4.23 mV`, `3.3 mV` hys | Clean trigger & reset | **PASS** |
| `S3.2-03` 3-Stage HV Filter `@ 100 kHz` | **`-227.86 dB`** (w/ `100 mΩ` ESR, `2 nH` ESL) | MNA `-227.86 dB` (`0.001 dB` diff) | `> 100 dB` (`< -100 dB`) | **PASS** |
| `S3.2-03` HV Filter Integrated Thermal Noise | **`0.142 µVrms`** | — | `< 10 µVrms` | **PASS** |
| Cold CSA `CSA_SUM` Stray Capacitance Budget | `0.109 pF` active bootstrapped (`0.775 pF` passive ref) | `In1/In2` keepout `x=34.0..55.2 mm` | `< 0.15 pF` | **PASS** |

## 3. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/ibic_cryo_frontend_v3/build_ibic_v3.py
PYTHONPATH=.:src pytest tests/test_pcb_kernel_and_ibic.py -v -p no:cacheprovider
```
