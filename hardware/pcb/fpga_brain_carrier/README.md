# FPGA Brain Carrier PCB (`XC7K325T-2FFG900` + `ZU48DR` 2U Rack ICD) & Live `ngspice-47` PDN Verification

**BOM Coverage:** `S3.3-01`, `S3.3-02`, `S3.3-04`, `S1.4-03`, `S4.5-03`, `S6.9-04`, plus `S6.11-01` (`ZU48DR` 2U Rack ICD Ref), `S3.3-03` (`FMC HPC` ADC port), `S7.4-01` (`10 MHz` Rb), `S7.4-02` (White Rabbit trigger).  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. All active semiconductors are `{Aday-COTS}` candidates.

## 1. Yosys-Grounded FPGA Sizing & `ZU48DR` 2U Rack ICD

Directly sized to real Yosys pre-P&R cell counts (`results/exp149_*/yosys_*_stat.json` and `results/stage2_rtl_verification/yosys_xc7_stat.json`):

| RTL Target / Device | LUTs | FFs | BRAM (`BRAM36-eq`) | DSP / MULT | Notes |
| :--- | ---: | ---: | ---: | ---: | :--- |
| `boed_q16_core` (`ecp5` Yosys) | `3,871` | `4,448` | `12 DP16KD` (`6.0`) | `106 MULT18X18D` | Exceeds `LFE5U-45F` (72 DSP) |
| `boed_q16_core` (`xc7` Yosys) | `5,467` | `3,080` | `12 RAMB18E1` (`6.0`) | `99 DSP48E1` | Single-channel BOED core |
| `boed_top_16ch` (`xcup` Yosys) | `102,886` | `59,157` | `192 RAMB18E2` (`96.0`) | `1,584 DSP48E2` | `24.2%` LUT / `37.1%` DSP on `ZU48DR` |
| `fpga_top_machine_ctrl` (`xc7`, BOED + all 6 controllers) | `14,252` | `10,517` | `12 RAMB18E1` (`6.0`) | `124 DSP48E1` | Full unified control brain |
| **Carrier `XC7K325T-2FFG900` Capacity** | **`203,800`** (`14.3×`) | **`407,600`** (`38.8×`) | **`445`** (`74.2×`) | **`840`** (**`6.77×`**) | **`> 4×` headroom across all resources** |
| **`S6.11-01` `ZU48DR` 2U Rack ICD Ref** | `2× XCZU48DR-2FFVG1517E` | `32` Direct-RF chains | `87.96 W` @ `300 K` (`0 W` cryo) | `250 MHz` (`2.336 µs`/step) | `482.6×520×88.9 mm`, `11.50 kg` |

## 2. 8-Layer Isola FR408HR Board Architecture (`fpga_brain_carrier.{kicad_sch,kicad_pcb}`)

- **Dimensions & Stackup:** `230 × 170 mm`, **`8` copper layers** (`SIG1-GND-SIG2-PWR-GND-SIG3-GND-SIG4`), `1.534 mm` total thickness, Isola FR408HR (`ε_r = 3.66`, `tanδ = 0.0092`). `In3.Cu` (`VCCINT_1V0` PWR) and `In4.Cu` (`GND2`) use `2 oz` (`0.070 mm`) copper over a `0.100 mm` thin core for low planar spreading inductance.
- **Controlled Impedance (`104 / 104` DRC checks PASS across all routed segments, `±5%`):**
  - `50 Ω SE` microstrip (`F.Cu`/`B.Cu`): `w = 0.2500 mm` → `Z0 = 50.00 Ω` on `10 MHz` Rb & White Rabbit SMA inputs.
  - `50 Ω SE` stripline (`In2.Cu`/`In5.Cu`): `w = 0.1726 mm` → `Z0 = 50.00 Ω` on `DDR4 DQ0..DQ3`.
  - `100 Ω diff` edge-coupled microstrip (`w = 0.2096 mm`, `s = 0.22 mm` → `Z_diff = 100.00 Ω`) & stripline (`In2.Cu`/`In5.Cu`, `w = 0.1421 mm`, `s = 0.22 mm` → `Z_diff = 100.00 Ω`): coupled `250/100/125 MHz` LVDS clocks with `B.Cu` backside via-in-pad `100 Ω` termination beneath `XC7K325T`, planar fly-by `DDR4 CK`, `FMC HPC` ADC lanes, isolated IBIC/Blanker LVDS ports, and `1000BASE-T` MDI pairs.
- **Subsystems:** `12 V` protected bus → `LM3880` power sequencer → `TPS546D24A` (`1.0 V VCCINT @ 15 A` + `64`-cap 5-decade PDN bank), `1.8 V`, `1.2 V DDR4 + 0.6 V TPS51200 VTT`, `2.5 V LVDS`, `3.3 V IO`, `2× LT3045` (`1.0 V/1.2 V` MGT); `LMK04828` dual-loop jitter cleaner + `CVHD-950` `100 MHz` VCXO; `2 GB` DDR4 (`2× MT40A512M16LY`), `256 Mb` QSPI NOR (`MT25QU256ABA`); `FMC HPC` (`ASP-134488-01`); `4×` isolated LVDS/SPI ports (`ADN4654`/`ADuM141D`: IBIC, Blanker, HV-DAC, AOM/Pyro + `1oo2D` Interlock); `DP83867IR` `1000BASE-T` GbE; `FT232HL` USB-UART; `14-pin` JTAG.
- **Strict EDA & Physical Copper Connectivity Verification:** `139` components, `126` nets, **`routed = 126 / 126` (`100%` pad-to-pad)**, **`unconnected_items = 0`**, **`track_dangling_count = 0`**, `1,625` copper segments, `468` vias, **`0` ERC errors**, **`0` DRC errors**, `SCH ↔ PCB` netlist parity PASS.

## 3. Live `ngspice-47` PDN AC Impedance & `5 A` Transient Verification (`fpga_pdn_1v0.cir`)

Executed natively with `ngspice-47 -b` (exit `0`, `0` errors, `0` warnings) modeling realistic VRM closed-loop impedance (`1.0 mΩ`, `14 nH`), 5-decade bulk+MLCC ESR/ESL (`4× 470 µF`, `8× 47 µF`, `12× 4.7 µF`, `16× 470 nF`, `24× 100 nF`), 2 oz plane spreading inductance, and `XC7K325T` FFG900 package/die capacitance:

| Metric | `ngspice-47` Measured | Independent Python MNA | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| Peak `|Z_PDN(f)|` (`100 Hz – 20 MHz`) | **`4.1604 mΩ`** (`@ 30.43 kHz`) | `4.1604 mΩ` (`0.0002%` diff) | `< 10 mΩ` | **PASS** |
| `|Z_PDN|` at `100 Hz` / `10 kHz` / `1 MHz` | `2.000` / `2.366` / `1.782 mΩ` | `2.000` / `2.366` / `1.782 mΩ` | `< 10 mΩ` | **PASS** |
| `|Z_PDN|` at `10 MHz` / `20 MHz` | `2.914` / **`3.210 mΩ`** | `2.913` / `3.209 mΩ` | `< 10 mΩ` | **PASS** |
| Transient `5 A` Load-Step Droop (`1→6 A`, `50 ns`) | **`16.21 mV`** (`1.621%`) | — | `< 30 mV` (`±3%`) | **PASS** |
| Transient `5 A` Load-Release Overshoot | **`6.23 mV`** (`0.623%`) | — | `< 30 mV` (`±3%`) | **PASS** |

## 4. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/fpga_brain_carrier/build_fpga_carrier.py
PYTHONPATH=.:src pytest tests/test_pcb_fpga_blanker_cryo.py -v -p no:cacheprovider
```
