# Cryo-RF, Microwave, Quench & rf-SET Harness ICD (`hardware/pcb/cryo_rf_harness_icd/`)

> **Epistemic Status:** `M0_M1_DESIGN_ONLY` (`no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`). All SPICE results below were executed live on rootless `ngspice-47`.

## 1. Scope (`17 E2` Parts + `S6.3-04` Quench Harness)
- **E2 Parts (`17`):** `S3.2-04, S6.4-03, S6.5-03, S6.6-01, S6.6-02, S6.6-03, S6.6-04, S6.6-07, S6.7-01, S6.10-01, S6.11-02, S6.11-03, S6.11-04, S9.3-02, S9.4-01, S9.4-02, S9.4-03`
- **Magnet Quench Harness (`1`):** `S6.3-04` (with `S7.SAFETY-05` external `1.563 Ohm` dump bank)

## 2. KiCad 8 Bulkhead Distribution PCB (`cryo_rf_bias_panel`)
- **Stackup:** 4-layer Rogers RO4350B (`er=3.48`, `0.254 mm` outer cores), `170 x 120 mm`
- **Verification:** **`0` ERC errors**, **`0` ERC warnings**, **`0` DRC errors**, SCH/PCB parity = **`True`**, **`routed_net_count = 59/59`**, **`unrouted_net_count = 0`**, **`unconnected_items = 0`**, **`track_dangling_count = 0`** (`278` segments, `74` vias)
- **Contents:** `94` components, `59` nets: `8x` 4 K InP HEMT bias channels, `4x` 20 mK TWPA flux-bias + Eccosorb CR-124 LPF lanes, `4x` `50.00 Ohm` controlled-impedance Rogers RO4350B RF/rf-SET bias-tee monitor lanes (`32` Z0 checks PASS), and `S6.3-04` `400 V` quench voltage-tap isolation bay protected by a `2.5 x 92 mm` milled `Edge.Cuts` air-slot (`1` HV checks PASS).

## 3. Live `ngspice-47` Simulation Verification
| Deck | BOM ID | Key Measured Metrics | Cross-Check Parity | Verdict |
|---|---|---|---|---|
| `qram_chebyshev_50_to_3k.cir` | `S9.4-02` | `max |S11|(4-8 GHz) = -39.5549 dB` (`<= -20 dB`), `min |S21| = -0.000723 dB` (`> -0.2 dB`), `BW(-20 dB) = 4.8154 GHz` (`3.5923-8.4077 GHz`) | Exact ABCD `|dS11| = 0.002 dB` | **PASS** |
| `magnet_quench_dump_1p563ohm.cir` | `S6.3-04` | `V_peak = 396.694 V` (`<= 400 V`), `tau = 0.37032 s` (`~0.370 s`), `E_dump = 18.817 / 18.9408 kJ` (**`99.347% >= 99%`**), `T_dump_peak = 38.05 C` | Analytical LR `|dtau| = 0.014%` | **PASS** |
| `rf_set_tank_biastee.cir` | `S6.7-01` | `f_res = 321.5 MHz` (`250-400 MHz`), `|Gamma(50k)| = 0.08215`, `|Gamma(200k)| = 0.47807`, `Delta|Gamma| = 0.39592`, DC-bias RF isolation = **`113.23 dB`** (worst `200-450 MHz`: `98.46 dB > 40 dB`) | Python MNA `|dGamma| = 0.0` | **PASS** |

## 4. 6-Stage Thermal & Attenuation Reconciliation (`Exp125` / `Exp140` / `Exp142`)
- **Staged RF Input Attenuation:** `-20 dB (4 K) / -10 dB (800 mK Still) / -10 dB (100 mK CP) / -20 dB (20 mK MXC)` (`-60 dB` total, cascaded `n_th(6 GHz, 20 mK) = 0.00505`).
- **Combined M4 `1,024`-Cell (`Exp140`) + Option-Q (`Exp142`) Cryo Loads:**
  - `20 mK (MXC)`: **`7.036 uW`** (`<= 14.0 uW` LD400 cap)
  - `100 mK (CP)`: **`65.73 uW`** (`<= 400.0 uW` cap)
  - `800 mK (Still)`: **`1.09 mW`** (`<= 40.0 mW` cap)
  - `4 K`: **`0.55 W`** (`<= 2.0 W` PT420 cap)
  - `50 K`: **`8.74 W`** (`<= 40.0 W` / `55.0 W` PT420 cap)
