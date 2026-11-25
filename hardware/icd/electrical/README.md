# Per-Part Electrical ICD Suite & Master Power / UPS / Timing Budget (`hardware/icd/electrical/`)

> **Epistemic Status:** `M0_M1_ELECTRICAL_ICD_DESIGN_ONLY` (`no_lab_measurement=true`, `no_supplier_quotes=true`, `iec61508_certified=false`, `semi_s2_certified=false`).

## 1. Coverage (`95 / 95` Non-E1 Electrical BOM Parts)
- **`E2` (`17` parts):** Cryo-RF, microwave, superconducting readout/bus & cryo-wiring harnesses
- **`E3` (`35` parts):** COTS rack HV/magnet/RF/MW/AWG/compute/timing/UPS/safety instruments
- **`E4` (`43` parts):** Electro-mechanical, HV-electrode, vacuum, piezo, heater & sensor electrical interfaces
- **Total BOM value covered:** `$3,434,800` nominal (`100%` cross-referenced to `BOM_DETAILED.csv`).

## 2. `S7.SAFETY-04` `15 kVA / 13.5 kW / 10 kWh` Online LFP UPS Reconciliation (`Exp150` + Conservative Loss/DoD)
- **Tier-1 Critical Safety / UHV / Control:** **`2533.0 W` (`2.533 kW`)** (`2325.0 W` from 95 ICDs + `208.0 W` E1 `S7.SAFETY-03`/`S6.11-01`):
  - **Exp150 Reference Formula (`10 kWh × 0.90 / 2.533 kW`):** **`213.2 min`** (`>= 180 min`)
  - **Conservative Battery Draw (`P_batt = 2533/0.90 + 350 W idle loss = 3164.44 W`) @ `100%` DoD (`10 kWh`):** **`189.6 min`** (`>= 180 min` PASS)
  - **Conservative Battery Draw @ `90%` Usable LFP DoD (`9.0 kWh`):** **`170.6 min`** (`< 180 min` — `tier1_conservative_90pct_dod_meets_180min: false`; requires `>= 10.55 kWh` [`11 kWh` nominal] LFP pack or `<= 2.385 kW` [`<= 2.35 kW`] Tier-1 trim)
- **Tier-2 Sheddable (`28` `TIER2_SHED` ICDs, `0.0 W` Discrepancy):**
  - Raw `supply_rails` steady sum (`28` parts) = **`18026.0 W`** = **`12275.0 W`** (`Exp150` Tier-2: `9.500 kW` PT420 + `2.195 kW` Option-HPC + `0.580 kW` S5.6/Option-Q) + **`5401.0 W`** (non-Exp150 auxiliary rack/facility incremental mains) + **`350.0 W`** (secondary HV/PXIe backplane rails already inside parent AC input)
- **Combined `Exp150` Envelope:** **`14.808 kW`** (`5.308 kW` pre-shed UPS bus excl. 3-phase PT420; rated `13.5 kW` runtime `40.0 min` nominal / `39.1 min` @ 100% DoD+350 W / `35.2 min` @ 90% DoD+350 W, all `>= 30 min` PASS)

## 3. Grounding Domains & Timing Fan-Out
- **5 Grounding Domains:** `AGND` (25), `DGND` (15), `HV_MINUS_5KV_DECK` (10), `CRYO_OVC` (21), `FACILITY_PE` (24) — total `95/95`.
- **`10 MHz` Rubidium Clock (`S7.4-01`):** Complete `16`-channel isolated fan-out (`CH1–CH16`).
- **White Rabbit Trigger (`S7.4-02`):** Complete `16`-port (`8×` SFP+ optical + `8×` `50 Ω` coax, `<200 ps` skew) fan-out.
