# Ion Column 20-Bit HV DAC, 5 kV 1000:1 Divider, 3-Stage Active Ripple Filter & `< 5 µs` Trim PCB

**BOM Coverage:** `S1.3-03`, `S2.3-04`, `S6.10-04` (interfacing `S1.1-05`, `S1.2-03`, `S1.5-03`, `S4.5-03` and `rtl/machine_ctrl/spi_dac_hv_ctrl.v`)  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. All active semiconductors are `{Aday-COTS}` candidate parts.

## 1. Board Summary & Strict KiCad 8 EDA Verification

| Parameter | Value / Measured Result | Requirement / Spec | Status |
| :--- | :--- | :--- | :---: |
| Stackup & Geometry | 4-layer Isola FR408HR (`ε_r=3.66`, CTI `≥ 600` MG-I), `220 × 150 mm`, `1.67 mm` thick | 4L HV PCB (`≥ 12 mm` @ `5 kV`) | **PASS** |
| Physical Routing & Connectivity | **`72 / 72` multi-pin nets routed (`100%`)**, `1,104` segments, `269` vias, **`0` unrouted**, **`0` unconnected**, **`0` dangling** | 100% pad-to-pad routed Union-Find DRC | **PASS** |
| Schematic / PCB Netlist | `102` components, `72` nets, `2` milled `Edge.Cuts` air-slots (L-shaped `5 kV` barrier) | Strict S-expr + SCH↔PCB parity | **PASS** |
| ERC / DRC Errors | **`0` ERC / `0` DRC** | `0 / 0` | **PASS** |
| `5 kV` HV Clearance / Creepage (`HV_5KV_*`) | **`14.020 mm`** air clearance, **`31.580 mm`** surface creepage around milled air-slots, `through_board_ok=true` | `≥ 12.0 mm` clr / `≥ 16.0 mm` crp (IEC 61010-1 / IPC-2221B) | **PASS** |
| Controlled-Impedance `50 Ω` Coax I/O (`12` checks) | `Z0 = 50.00 Ω` (`0.001%` max error on `F.Cu`) | `50 Ω ± 5%` | **PASS** |

## 2. Architecture

- **HV Isolation Bay (`x = 10..84 mm`, `y = 14..56 mm`):** `5 kV` alumina-standoff turrets (`S1.1-05` in; `S1.3-03` landing, `S2.3-04` mini-lens, `S1.2-03` Wien, `S1.5-03` HDA outputs), 3-stage `10 kΩ / 10 nF` (`5 kV` Ohmite MOX + `6 kV` WIMA FKP1) RC ripple filter with closed-loop `ADA4898-1` anti-phase ripple cancellation, plus hard-wired `HV_SAFE_CLAMP` (`Gigavac G81C` `10 kV` NC vacuum relay + `Ohmite MOX-4 500 kΩ` dump resistor + `IXTH1N450HV` `4.5 kV` MOSFET backup).
- **Milled `Edge.Cuts` Air-Slots:** L-shaped HV barrier enclosing the `5 kV` top-left bay (`x ≤ 86 mm, y ≤ 54 mm`): vertical `4.0 × 74.0 mm` slot (`x = 96..100 mm, y = 8..82 mm`) straddled by the `36 mm`-pitch `Caddock USF370` `99.900 MΩ` precision divider resistor & `2.0 pF` compensation cap, paired with horizontal `80.0 × 4.0 mm` slot (`y = 68..72 mm`) isolating `5 kV` hot nodes from `HV_RTN` / LV clamp coils while providing a clean LV routing corridor below `y = 86 mm`.
- **20-Bit Ultra-Low-Noise DAC & Trim Bay (`x = 114..216 mm`):** `ADuM1401` isolated `spi_dac_hv_ctrl.v` SPI/LDAC/CLR/CLAMP interface, `4× AD5791BRUZ` 20-bit DACs with `LT6655B-5` + `OPA211` `±10 V` reference, `Vishay Z201 100.00 kΩ` `1000:1` low-side divider + `ADA4522-1`/`OPA211` HV servo error integrator, `THS4031` fast `< 5 µs` on-the-fly interferometer deflector trim summer (`S4.5-03`), and `LT3045/LT3094/ADP7142` ultra-low-noise LDO tree.

## 3. Live `ngspice-47` & Independent MNA Results (`ion_hv_filter_trim.cir`)

| Metric | `ngspice-47` Measured | Independent Python MNA Ref | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| `100 kHz` Active 3-Stage HV Ripple Rejection | **`-125.814 dB`** (`+17.91 dB` active boost) | Passive `-107.907 dB` vs MNA `-107.9086 dB` (`0.0016 dB` diff) | `> 80 dB` (`< -80 dB`) | **PASS** |
| Output Ripple for `10 Vpp @ 100 kHz` on `5.000 kV` | **`0.147 mVpp`** (`t = 1.52–1.60 ms`) | Asymptotic steady-state `5.12 µVpp` | `< 1 mVpp` (`< 2 mVpp` `S2.3-04`) | **PASS** |
| Precision `1000:1` Caddock HV Feedback Divider | `5000.000 V → 4.999995 V` (ratio **`1000.001`**, `1.0 ppm` err) | MNA `1000.000` | `≤ 100 ppm` (`dE/E ≤ 1e-4`) | **PASS** |
| Fast Deflector Trim Summer Step (`S4.5-03`) | `10–90%` rise **`0.732 µs`**, `1%` settle **`1.561 µs`** | — | `< 5.0 µs` | **PASS** |
| M4 20-Bit Dipole Gate DAC Spot Noise (`S6.10-04`) | **`8.587 nV/√Hz`** `@ 1.0 kHz` (`1.735 µVrms` `10 Hz–1 MHz`) | — | `< 500 nV/√Hz` (`< 0.5 µV/√Hz`) | **PASS** |

## 4. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/ion_column_hv_dac/build_ion_column_hv_dac.py
PYTHONPATH=.:src pytest tests/test_pcb_hv_laser_safety.py -v -p no:cacheprovider
```
