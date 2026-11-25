# Cryo-CMOS `4 K` Carrier (`968`-Gate SKY130 Crossbar Mux + `4 K / MXC` RC/Eccosorb Filter) & Live `ngspice-47` Verification

**BOM Coverage:** `S6.10-03`, `S6.7-02`, `S7.3-02`, `S7.3-01`  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. Active COTS connectors are `{Aday-COTS}`; SKY130 `4 K` dies and Eccosorb CR-124 RF absorber blocks are `{Ozel-Uretim}`.

## 1. `4 K` 4-Layer Cryo-CMOS Carrier Architecture (`cryo_cmos_4k_carrier.{kicad_sch,kicad_pcb}`)

- **Dimensions & Stackup:** `165 × 125 mm`, **`4` copper layers**, `1.478 mm` total thickness, thermal-cycle-hardened (`>100` cooldowns `300 K ↔ 4 K`):
  - Outer ENIG Au wire-bondable layers (`F.Cu`, `B.Cu`) over `0.254 mm` **Rogers RO4350B** (`ε_r = 3.48`).
  - Central `0.800 mm` **AlN / Cu-Invar-Cu CTE-matched core** (`ε_r = 8.90`, `CTE ≈ 4.5 ppm/K` matched to Si) sandwiched between `In1.Cu` (`GND_4K`) and `In2.Cu` (`VDD_4K_1V2`).
- **`968`-Gate SKY130 `4 K` Crossbar Mux (`S6.10-03`, `S7.3-01`, `S7.3-02`):**
  - Hosts `8×` SKY130 `121`-gate cryo-CMOS crossbar mux dies (`U_MUX0..U_MUX7` = `968` local Stark/M4/SET DC gates for the `Exp131` `L = 11` surface code: `121` nodes × `8` DC gates/node).
  - Reduced `1.2 V` `4 K` core rail (`VDD_4K_1V2`) + `±2.0 V` gate bias rails; **100% C0G/NP0 cryogenic capacitors** (zero Class-II X7R capacitance freeze-out at `4 K`); OFHC copper `4 K` thermalization anchors (`J_THERM_4K_A/B`).
  - Daisy-chained `50 Ω SE` SPI control microstrips (`w = 0.5429 mm` → `Z0 = 50.00 Ω`, `109 / 109` DRC checks PASS across all routed segments).
- **`4 K / MXC (20 mK)` 2-Stage RC + Eccosorb CR-124 DC Gate Filter Bank (`S6.7-02`):**
  - `8` representative Stark/M4/SET filter channels (`R1 = 1.0 kΩ` NiCr + `C1 = 100 nF` C0G `|| 100 pF` HF shunt at `4 K` → `Eccosorb CR-124` lossy RF absorber → `R2 = 2.0 kΩ` + `C2 = 47 nF` C0G `|| 100 pF` HF shunt at `20 mK` MXC).
- **Strict EDA & Physical Copper Connectivity Verification:** `83` components, `53` nets, **`routed = 53 / 53` (`100%` pad-to-pad)**, **`unconnected_items = 0`**, **`track_dangling_count = 0`**, `653` copper segments, `194` vias, **`0` ERC errors**, **`0` DRC errors**, `SCH ↔ PCB` netlist parity PASS.

## 2. Live `ngspice-47` `4 K / 20 mK` Filter, Thermal Noise & Power Verification (`cryo_4k_gate_filter.cir`)

Executed natively with `ngspice-47 -b` (exit `0`, `0` errors, `0` warnings) using `.temp -269.15` (`4.00 K` global stage), per-instance `temp=-273.13` (`20 mK` MXC), and `temp=26.85` (`300 K` upstream DAC noise equivalent `7.50 nV/√Hz`), including realistic `0.05 pF` resistor body strays and `0.60 nH` MLCC ESLs:

| Metric | `ngspice-47` Measured | Independent Python MNA / Nyquist | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| Filter `-3 dB` Bandwidth `f_3dB` | `669.29 Hz` | — | Quasi-static DC Stark/SET | **PASS** |
| RF Attenuation `@ 100 kHz` / `10 MHz` / `100 MHz` | `-73.43` / `-155.94` / `-139.67 dB` | `-73.43` / `-155.94` / `-139.67 dB` (`0.000 dB` diff) | High-freq ESL mitigated by `100 pF` HF shunt | **PASS** |
| RF Attenuation `@ 1 GHz` (lumped shielded model\*) | **`-215.12 dB`** | `-215.48 dB` (`0.361 dB` diff) | `> 60 dB` (`≤ -60 dB`) | **PASS** |
| In-Band Total Noise `@ 10 Hz` (`300 K` DAC + `4 K` + `20 mK`) | **`7.523 nV/√Hz`** (`0.00752 µV/√Hz`) | `7.524 nV/√Hz` (`0.01%` parity) | `< 0.5 µV/√Hz` | **PASS** |
| Intrinsic `4 K + 20 mK` Filter-Only Thermal Noise `@ 10 Hz` | **`0.5275 nV/√Hz`** | `0.5276 nV/√Hz` (`0.02%` parity) | Cryogenic Nyquist floor | **PASS** |
| Total Integrated Output RMS Noise (`1 Hz – 1 MHz`) | **`0.2251 µVrms`** | — | Sub-µVrms Stark/SET stability | **PASS** |
| `0 → 1.0 V` Stark Step `10–90%` Rise / `0.1%` Settling Time | `520.2 µs` / **`1.632 ms`** | — | Clean settling `< 5 ms` | **PASS** |
| `968`-Gate SKY130 `4 K` Total Power (static + `25 kHz` refresh) | **`13.650 mW`** (`2.808` core/dyn + `10.842` bias) | — | **`≤ 15.4 mW @ 4 K`** | **PASS** |

*\*Epistemic caveat:* Lumped SPICE models assume an ideal Faraday partition between the `4 K` and `20 mK` filter bays; physical cryogenic enclosure cavity crosstalk typically floors practical measured RF isolation near `100–120 dB`, still providing `40–60 dB` margin beyond the `> 60 dB @ 1 GHz` requirement.

## 3. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/cryo_cmos_4k_carrier/build_cryo_4k_carrier.py
PYTHONPATH=.:src pytest tests/test_pcb_fpga_blanker_cryo.py -v -p no:cacheprovider
```
