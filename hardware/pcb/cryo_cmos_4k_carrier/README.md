# Cryo-CMOS `4 K` Carrier (`968`-Gate SKY130 Crossbar Mux + `4 K / MXC` RC/Eccosorb Filter) & Live `ngspice-47` Verification

**BOM Coverage:** `S6.10-03`, `S6.7-02`, `S7.3-02`, `S7.3-01`  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. Active COTS connectors are `{Aday-COTS}`; SKY130 `4 K` dies and Eccosorb CR-124 RF absorber blocks are `{Ozel-Uretim}`.

## 1. `4 K` 4-Layer Cryo-CMOS Carrier Architecture (`cryo_cmos_4k_carrier.{kicad_sch,kicad_pcb}`)

- **Dimensions & Stackup:** `165 × 125 mm`, **`4` copper layers**, `1.478 mm` total thickness, thermal-cycle-hardened (`>100` cooldowns `300 K ↔ 4 K`):
  - Outer ENIG Au wire-bondable layers (`F.Cu`, `B.Cu`) over `0.254 mm` **Rogers RO4350B** (`ε_r = 3.48`).
  - Central `0.800 mm` **AlN / Cu-Invar-Cu CTE-matched core** (`ε_r = 8.90`, `CTE ≈ 4.5 ppm/K` matched to Si) sandwiched between `In1.Cu` (`GND_4K`) and `In2.Cu` (`VDD_4K_1V2`).
- **Thermal Isolation Split (`OBS-019`):** `4 K` (`GND_4K`, `x ≤ 112 mm`, `J_THERM_4K_A/B`) and `20 mK` MXC (`GND_MXC`, `x ≥ 118 mm`, `J_THERM_MXC`, `R2_MXC`/`C2_MXC`/`J_MXC_GATE_A/B`) copper planes are physically split across a `6.0 mm` copper-free thermal break moat (`5.0 mm` multi-layer `THERMAL_ISOLATION_4K_TO_MXC` keepout), eliminating the `~34.8 mW` unbroken copper plane thermal short; full dilution-fridge build mounts Stage-2 on a separate MXC daughterboard via NbTi/manganin Eccosorb harnesses.
- **`968`-Gate SKY130 `4 K` Crossbar Mux (`S6.10-03`, `S7.3-01`, `S7.3-02`, `OBS-091` / `OBS-135`):**
  - Hosts `8×` SKY130 `121`-gate cryo-CMOS crossbar mux dies (`U_MUX0..U_MUX7` = `968` local Stark/M4/SET DC gates for the `Exp131` `L = 11` surface code: `121` nodes × `8` DC gates/node; `8` representative bank outputs routed to the filter array).
  - Real `0.635 mm` pitch Omnetics Bi-Lobe Nano-D connectors (`Connector_Omnetics:NanoD_2x4_P0.635mm`, G-S-G-S high-speed pinout); per-chip `100 nF C0G/NP0` decoupling on ALL 3 rails (`VDD_4K_1V2`, `VBIAS_POS_2V`, `VBIAS_NEG_2V`; zero Class-II X7R freeze-out); SKY130 `±2.0 V` (`4.0 V` span) gate-hold buffers require `5 V` thick-oxide (`g5v0d10v5`) triple-well devices tied to `-2.0 V` and `4 K` BSIM4 PDK verification at M2 (`NMOS_SKY4K`/`PMOS_SKY4K` in SPICE are `LEVEL=1` behavioral effective-`V_th` switches).
  - Controlled `50 Ω SE` SPI microstrips across ALL SPI nets INCLUDING daisy-chain hops `SPI_CHAIN_0_1..6_7` (`w = 0.5429 mm` → `Z0 = 50.00 Ω`, `193 / 193` DRC checks PASS, adjacent `GND_4K` stitching vias `< 3.5 mm` from every die).
- **`4 K / MXC (20 mK)` 2-Stage RC + Eccosorb CR-124 DC Gate Filter Bank (`S6.7-02`):**
  - `8` representative Stark/M4/SET filter channels (`R1 = 1.0 kΩ` NiCr + `C1 = 100 nF` C0G `|| 100 pF` HF shunt w/ `1.0 Ω` NiCr ESL-damping ESR at `4 K` → `Eccosorb CR-124` → `6.0 mm` thermal moat → `R2 = 2.0 kΩ` + `C2 = 47 nF` C0G `|| 100 pF` HF shunt on isolated `GND_MXC` at `20 mK`).
- **Strict EDA & Physical Copper Connectivity Verification:** `100` components, `54` nets, **`routed = 54 / 54` (`100%` pad-to-pad)**, **`unconnected_items = 0`**, **`track_dangling_count = 0`**, `782` copper segments, `251` vias, **`0` ERC errors**, **`0` DRC errors**, `SCH ↔ PCB` netlist parity PASS.

## 2. Live `ngspice-47` `4 K / 20 mK` Filter, Thermal Noise & Power Verification (`cryo_4k_gate_filter.cir`)

Executed natively with `ngspice-47 -b` (exit `0`, `0` errors, `0` warnings) using `.temp -269.15` (`4.00 K` global stage), per-instance `temp=-273.13` (`20 mK` MXC), and `temp=26.85` (`300 K` upstream DAC noise equivalent `7.50 nV/√Hz`), including realistic `0.05 pF` resistor body strays, `0.60 nH` MLCC ESLs with `1.0 Ω` HF damping ESR, and FULL bipolar `±2.0 V` (`+2.0 V` AND `-2.0 V` rail) power accounting:

| Metric | `ngspice-47` Measured | Independent Python MNA / Nyquist | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| Filter `-3 dB` Bandwidth `f_3dB` | `669.29 Hz` | — | Quasi-static DC Stark/SET | **PASS** |
| RF Attenuation `@ 1 GHz` (w/ `1.0 Ω` ESL damping) | **`-172.82 dB`** | `-172.83 dB` (`0.009 dB` diff) | `> 60 dB` (`≤ -60 dB`) | **PASS** |
| In-Band Total Noise `@ 10 Hz` (`300 K` DAC + `4 K` + `20 mK`) | **`7.523 nV/√Hz`** (`0.00752 µV/√Hz`) | `7.524 nV/√Hz` (`0.01%` parity) | `< 0.5 µV/√Hz` | **PASS** |
| Intrinsic `4 K + 20 mK` Filter-Only Thermal Noise `@ 10 Hz` | **`0.5275 nV/√Hz`** | `0.5276 nV/√Hz` (`0.02%` parity) | Cryogenic Nyquist floor | **PASS** |
| Total Integrated Output RMS Noise (`1 Hz – 1 MHz`) | **`0.2251 µVrms`** | — | Sub-µVrms Stark/SET stability | **PASS** |
| `0 → 1.0 V` Stark Step `10–90%` Rise / `0.1%` Settling Time | `520.2 µs` / **`1.632 ms`** | — | Clean settling `< 5 ms` | **PASS** |
| `968`-Gate SKY130 `4 K` Total Power (incl. `+2 V` & `-2 V` rails) | **`13.636 mW`** (`2.808` core/dyn + `5.414` `+2 V` + `5.414` `-2 V`) | — | **`≤ 15.4 mW @ 4 K`** | **PASS** |

*\*Epistemic caveat:* Lumped SPICE models assume an ideal Faraday partition between the `4 K` and `20 mK` filter bays; physical cryogenic enclosure cavity crosstalk typically floors practical measured RF isolation near `100–120 dB`, still providing `40–60 dB` margin beyond the `> 60 dB @ 1 GHz` requirement.

## 3. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/cryo_cmos_4k_carrier/build_cryo_4k_carrier.py
PYTHONPATH=.:src pytest tests/test_pcb_fpga_blanker_cryo.py -v -p no:cacheprovider
```
