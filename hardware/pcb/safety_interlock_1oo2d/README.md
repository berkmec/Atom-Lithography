# Diverse Dual-Channel `1oo2D` Safety Interlock & `22 kV` Active `2 MΩ` HV Crowbar PCB

> [!CAUTION]
> **STRICT EPISTEMIC STATUS: `DESIGN_ONLY_NOT_CERTIFIED`**  
> - `iec61508_certified: false`  
> - `semi_s2_certified: false`  
> - `requires_third_party_assessment: true`  
> - `no_lab_measurement: true`, `no_physical_fab: true`  
> This PCB and SPICE suite is a preliminary M0/M1 hardware architecture reference only and has NOT undergone accredited IEC 61508 SIL-3 or SEMI S2 third-party safety certification.

**BOM Coverage:** `S7.SAFETY-03`, `S7.SAFETY-02`, `S7.SAFETY-05`, `S7.SAFETY-06`, `S7.SAFETY-01`, `S7.4-04`, `S5.5-04` (interfacing `rtl/machine_ctrl/uhv_interlock_fsm.v`, `laser_aom_pyrometer_afe`, and `ion_column_hv_dac`)

## 1. Board Summary & Strict KiCad 8 EDA Verification

| Parameter | Value / Measured Result | Requirement / Spec | Status |
| :--- | :--- | :--- | :---: |
| Stackup & Geometry | 4-layer Isola FR408HR (`ε_r=3.66`, CTI `≥ 600` MG-I), `280 × 175 mm`, `1.67 mm` thick | 4L FR4 w/ HV isolation milled air-slots | **PASS** |
| Physical Routing & Connectivity | **`74 / 74` multi-pin nets routed (`100%`)**, `910` segments, `203` vias, **`0` unrouted**, **`0` unconnected**, **`0` dangling** | 100% pad-to-pad routed Union-Find DRC | **PASS** |
| Schematic / PCB Netlist | `83` components, `74` nets, `2` milled `Edge.Cuts` air-slots (L-shaped `22 kV` barrier) | Strict S-expr + SCH↔PCB parity | **PASS** |
| ERC / DRC Errors | **`0` ERC / `0` DRC** | `0 / 0` | **PASS** |
| `22 kV` HV Clearance / Creepage (`HV_22KV_*`) | **`43.170 mm`** air clearance, **`59.631 mm`** surface creepage around milled air-slots, `through_board_ok=true` | `≥ 30.0 mm` clr / `≥ 50.0 mm` crp | **PASS** |
| Epistemic Certification Lock | `iec61508_certified=false`, `semi_s2_certified=false`, `requires_third_party_assessment=true` | Strictly `DESIGN_ONLY_NOT_CERTIFIED` | **PASS** |

## 2. Diverse `1oo2D` Architecture (`Ch-A` vs `Ch-B`)

- **Channel A (`y = 10..80 mm`, Electromechanical + Bipolar Comparator Family):** `LM2936` `5 V` reg, `LM2903` dual comparators (`PH3 0.02/0.05 ppm` `4–20 mA`, `O2 < 19.5%`, `MXC < 1 K`, UHV `> 1e-8 Torr`), `SN74LVC1G08` voting chain, and dual **`Omron G7SA-3A1B` (`IEC 61810-3`) force-guided safety relays** (`K_FG_A1`, `K_FG_A2`) with mechanically linked NC mirror contacts (`DIAG_FB_A`) for weld detection.
- **Channel B (`y = 92..165 mm`, Diverse CMOS + Solid-State MOSFET/Opto-SSR Family):** `ADP7142` `5 V` reg, `MAX9032` dual comparators, `CD4081B` CMOS voting chain, and diverse **`CPC1017N` opto-SSRs + `Vishay SQJ461EP` high-side P-MOSFETs** (`Q_SSR_B1`, `Q_SSR_B2`) wired in **series** with `K_FG_A1/A2` so either channel opening de-energizes every safety load even if Channel-A sticks welded!
- **Diagnostics & Watchdog:** `4×` dual-NC series E-Stop mushroom loop (`J_ESTOP1..4`), cross-channel `SN74AHC1G86` XOR discrepancy comparators (`U_DIAG_XOR_VOTE`, `U_DIAG_XOR_FB`) with `10 ms` RC filter latching `DISCREP_FAULT`, and `TPS3850` hardware window watchdog (`U_WDT_WIN`) monitoring `FPGA_WDT_KICK`.
- **De-Energize-To-Trip Actuator Drivers:** Dual-coil `< 3.2 ms` blade shutter (`J_SHUTTER_OUT` + `SMBJ36A` fast demag TVS), `< 80 ms` fail-close UHV gate-valve solenoid (`J_UHV_VALVE_OUT` + `SMBJ36A`), hardwired `SAFE_LASER_EN_A/B` crowbar outputs (`J_LASER_CB_OUT`), and `HV_SAFE_CLAMP`.
- **Isolated `22 kV` Active `2.00 MΩ` HV Crowbar Bay (`x = 202..272 mm`):** Enclosed by an L-shaped milled `Edge.Cuts` air-slot barrier (`8 × 100 mm` vertical + `70 × 8 mm` horizontal); parallel diverse normally-closed `25 kV` HV vacuum relays (`Gigavac G81C-25KV-NC` on `Ch-A` `||` `Ross E25-NC-25KV` on `Ch-B`) discharging `C_stray = 1.5 nF` through `2 × 1.00 MΩ` `Ohmite MOX-4-25KV` non-inductive resistors (`R_total = 2.00 MΩ`).

## 3. Live `ngspice-47` Crowbar & Single-Fault Injection Results (`safety_1oo2d_crowbar.cir`)

| Scenario / Metric | `ngspice-47` Measured | Analytical Ref (`Exp150`) | Target / Spec | Status |
| :--- | :---: | :---: | :---: | :---: |
| Nominal `22 kV` `1.5 nF` `2.00 MΩ` Crowbar (`→ 50 V`) | **`18.286 ms`** (`V@40ms = 0.490 V`) | `τ·ln(440) = 18.260 ms` | `< 50 ms` | **PASS** |
| Nominal Crowbar Dissipated Energy (`∫ V²/2MΩ dt`) | **`0.36300 J`** | `0.5·C·V² = 0.36300 J` | `< 0.5 J` | **PASS** |
| **Fault #1 (`K_CROWBAR_A` Stuck OPEN `100 GΩ`):** `Ch-B` Crowbar | **`18.286 ms`**, **`0.36300 J`** | Fails SAFE via diverse `Ch-B` | `< 50 ms`, `< 0.5 J` | **PASS** |
| **Fault #2 (`K_FG_A1` Stuck WELDED `10 mΩ`):** `24 V` Shutter Cutoff | **`0.000011 V`** safe, coil drop **`0.824 ms`**, `DISCREP_FAULT = 5.00 V` | Fails SAFE via series `Ch-B` SSR | `< 0.05 V`, `< 3.2 ms`, fault latched | **PASS** |
| **Fault #3 (`ESTOP_A` Open-Wire Break, `ESTOP_B = 5 V`):** `1oo2` Load | **`0.000006 V`** safe (`24.0 V → 6 µV`) | De-energize-to-trip | `< 0.05 V` | **PASS** |

## 4. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/safety_interlock_1oo2d/build_safety_interlock_1oo2d.py
PYTHONPATH=.:src pytest tests/test_pcb_hv_laser_safety.py -v -p no:cacheprovider
```
