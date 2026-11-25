# Laser `80–200 MHz` AOM RF VCA, `10 µs` 2-Color Pyrometer TIA, `1.0 ms` Integrator & `< 0.1 ms` Crowbar PCB

**BOM Coverage:** `S5.5-03`, `S5.5-01`, `S5.5-04`, `S5.3-03` (interfacing `rtl/machine_ctrl/aom_pid_ctrl.v` and `safety_interlock_1oo2d`)  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. All active semiconductors are `{Aday-COTS}` candidate parts.

## 1. Board Summary & Strict KiCad 8 EDA Verification

| Parameter | Value / Measured Result | Requirement / Spec | Status |
| :--- | :--- | :--- | :---: |
| Stackup & Geometry | 4-layer Rogers RO4350B (`ε_r=3.48`, `0.254 mm` outer RF/TIA layers) + Isola FR408HR (`0.800 mm` core), `185 × 125 mm` | 4L Rogers/FR4 mixed-signal PCB | **PASS** |
| Physical Routing & Connectivity | **`63 / 63` multi-pin nets routed (`100%`)**, `835` segments, `221` vias, **`0` unrouted**, **`0` unconnected**, **`0` dangling** | 100% pad-to-pad routed Union-Find DRC | **PASS** |
| Schematic / PCB Netlist | `75` components, `63` nets, `2` closed 3D via-tied `AGND` TIA guard cages (`connect_guard_ring`), `2` `In1/In2` TIA copper keepouts | Strict S-expr + SCH↔PCB parity | **PASS** |
| ERC / DRC Errors | **`0` ERC / `0` DRC** | `0 / 0` | **PASS** |
| Controlled-Impedance `50 Ω` RF Chain (`14` checks) | `Z0 = 50.00 Ω` (`w = 0.5429 mm`, `0.001%` max error across `80–200 MHz` AOM RF path) | `50 Ω ± 5%` | **PASS** |

## 2. Architecture

- **2-Color Fast Pyrometer TIA (`S5.5-03`, `S5.3-03`, `900–1700 K`, `τ_rise ≤ 10 µs`):**
  - InGaAs `1550 nm` (`Hamamatsu G12180-010A`, `OPA657NB`, `R_f = 100 kΩ`, `C_f = 12 pF`) + Si `850 nm` (`Hamamatsu S5971`, `OPA657NB`, `R_f = 200 kΩ`, `C_f = 6.0 pF`) with `F.Cu` guard rings and `In1/In2` copper keepouts feeding dual `ADS8860` 16-bit `1 MS/s` ADCs.
  - Dedicated `TLV3501` hardware over-temperature comparator (`T ≥ 1687 K` Si melt backup) hardwired directly into the local crowbar gate.
- **Inline `1.0 ms` Photodiode Pulse-Energy Integrator (`S5.5-03`):** `Hamamatsu S1223-01` pickoff photodiode → `OPA140` JFET Miller integrator (`C_INT = 100 nF` C0G `±0.5%`, `ADG1211` low-charge-injection reset switch) → `ADS8860` 16-bit ADC + `50 Ω` SMA diagnostic tap.
- **`80–200 MHz` AOM RF VCA Stage (`S5.5-01`, `aom_pid_ctrl.v`):** `AD5541A` 16-bit `100 kHz` SPI DAC + `LT6655B-2.5` ref → `ADA4898-1` VCA driver (`[0.65, 1.40]` gain) → `AD8367` `50 Ω` VCA → `ADG901/HMC547A` `< 15 ns` absorptive RF kill switch → `ADL5602` `50 Ω` output amplifier.
- **`< 0.1 ms` Hardware Crowbar (`S5.5-04`, wired directly to `safety_interlock_1oo2d`):** Dual `ACPL-072L` `< 60 ns` optocouplers (`SAFE_LASER_EN_A`, `SAFE_LASER_EN_B`) in hardware `1oo2` AND gating: (1) `2N7002` VCA zero-clamp, (2) RF kill switch, and (3) series dual-MOSFET `SI2302` `24 V` diode-laser enable cutoff.

## 3. Live `ngspice-47` & Independent MNA Results (`laser_pyro_tia_aom.cir`)

| Metric | `ngspice-47` Measured | Independent Python MNA Ref | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| InGaAs `1550 nm` TIA `10–90%` Rise Time | **`2.636 µs`** (`f_-3dB = 132.65 kHz`) | MNA `Z_dc = 99,996.16 Ω` (`0.00004%` diff) | `τ_rise < 10 µs` | **PASS** |
| Si `850 nm` TIA `10–90%` Rise Time | **`2.636 µs`** (`f_-3dB = 132.65 kHz`) | MNA `Z_dc = 199,992.32 Ω` | `τ_rise < 10 µs` | **PASS** |
| `1.0 ms` Pulse-Energy Integrator `2×` Sweep | `1× = 0.999993 V`, `2× = 1.999990 V` (**`0.00001%`** lin err, `0.000 mV` reset) | Ideal `2.00000×` | `< 1.0%` (`±1.5%` BOM) | **PASS** |
| AOM VCA Gain Modulation & RF Flatness | `1.40 / 0.65` ratio **`2.1538`**, `80–200 MHz` flatness **`0.0008 dB`** | Exact `2.15385` | `[0.65, 1.40]`, `< 0.5 dB` | **PASS** |
| Hardware Crowbar Cutoff (`SAFE_LASER_EN_A = 0`) | VCA clamp **`0.273 µs`**, `24 V` Diode-EN **`4.870 µs`** (`23.93 V → 0.12 mV`) | — | `< 50 µs` (`<< 0.1 ms`) | **PASS** |

## 4. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/laser_aom_pyrometer_afe/build_laser_aom_pyrometer_afe.py
PYTHONPATH=.:src pytest tests/test_pcb_hv_laser_safety.py -v -p no:cacheprovider
```
