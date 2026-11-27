# Per-Part Electrical ICD Suite & Master Power / UPS / Timing Budget (`hardware/icd/electrical/`)

> **Epistemic Status:** `M0_M1_ELECTRICAL_ICD_DESIGN_ONLY` (`no_lab_measurement=true`, `no_supplier_quotes=true`, `iec61508_certified=false`, `semi_s2_certified=false`).

## 1. Coverage (`95 / 95` Non-E1 Electrical BOM Parts)
- **`E2` (`17` parts):** Cryo-RF, microwave, superconducting readout/bus & cryo-wiring harnesses
- **`E3` (`35` parts):** COTS rack HV/magnet/RF/MW/AWG/compute/timing/UPS/safety instruments
- **`E4` (`43` parts):** Electro-mechanical, HV-electrode, vacuum, piezo, heater & sensor electrical interfaces
- **Total BOM value covered:** `$3,434,800` nominal (`100%` cross-referenced to `BOM_DETAILED.csv`).

## 2. `S7.SAFETY-04` `15 kVA / 13.5 kW / 12.0 kWh` Online LFP UPS Reconciliation (`Exp150` + Utility-Side Tier-2 Contactor + `90%` DoD)
- **Utility-Side Fast Contactor Ahead of UPS (`<5 ms`):** Sheds `12.500 kW` PT420 (`S6.1-02` Cryomech CPA1110 `12.42 kW` + `S6.9-01` `80 W`) and heavy Tier-2 mains **ahead of the UPS** so the `13.5 kW` UPS inverter is never overloaded (`peak UPS load = 5.378 kW <= 13.5 kW`, `39.84%` utilization).
- **Tier-1 Critical Safety / UHV / Control:** **`2533.0 W` (`2.533 kW`)** (`2325.0 W` from 95 ICDs + `208.0 W` E1 `S7.SAFETY-03`/`S6.11-01`) + **Tier-1B 120 s Controlled Ramp-Down (`2845.0 W`):** `650.0 W` dedicated `S6.3-05` `±300 A` magnet ramp-down branch + `2,195.0 W` `S9.HPC` graceful halt:
  - **Conservative Battery Draw (`P_batt = 2533/0.90 + 350 W idle loss = 3164.44 W`) @ `90%` Usable LFP DoD (`10.8 kWh`, incl. `120 s` Tier-1B):** **`202.8 min`** (`>= 180 min` **PASS**; steady-only `204.8 min`; legacy `10 kWh` pack gave `170.6 min < 180 min`)
  - **Conservative Battery Draw @ `100%` DoD (`12.0 kWh`):** **`225.5 min`** (`>= 180 min` PASS)
  - **Exp150 Nominal Reference (`12.0 kWh × 0.90 / 2.533 kW`):** **`255.8 min`**
- **Tier-2 Sheddable (`28` `TIER2_SHED` ICDs, `0.0 W` Discrepancy):**
  - Raw `supply_rails` steady sum (`28` parts) = **`21026.0 W`** = **`15275.0 W`** (`Exp150` Tier-2: `12.500 kW` PT420 utility-side + `2.195 kW` Option-HPC + `0.580 kW` S5.6/Option-Q) + **`5401.0 W`** (non-Exp150 auxiliary rack/facility incremental mains) + **`350.0 W`** (secondary HV/PXIe backplane rails already inside parent AC input)
- **Full-Load `13.5 kW` Rated Runtime:** `43.2 min` Exp150 reference / `46.9 min` @ 100% DoD+350 W / `42.2 min` @ 90% DoD+350 W (all `>= 30 min` PASS)

## 3. Grounding Domains & Timing Fan-Out
- **5 Grounding Domains:** `AGND` (25), `DGND` (15), `HV_MINUS_5KV_DECK` (10), `CRYO_OVC` (21), `FACILITY_PE` (24) — total `95/95`.
- **`10 MHz` Rubidium Clock (`S7.4-01`):** Complete `16`-channel isolated fan-out (`CH1–CH16`).
- **White Rabbit Trigger (`S7.4-02`):** Complete `16`-port (`8×` SFP+ optical + `8×` `50 Ω` coax, `<200 ps` skew) fan-out.
