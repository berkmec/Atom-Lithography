# Blanker ASIC Mezzanine PCB (`256-ch` `4×64` SKY130, `5 kV` Isolation, `53.3 V` HV Driver) & Live `ngspice-47` Verification

**BOM Coverage:** `S2.4-02`, `S2.4-01`, `S2.2-03`, `S2.4-03`, `S2.2-01`  
**Epistemic Status:** `M0/M1_DESIGN_ONLY` — `no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`. Active semiconductors are `{Aday-COTS}` candidates; SKY130 tiles & LTCC/MEMS interfaces are `{Ozel-Uretim}`.

## 1. Modular `256-ch` (`4×` Boards = `1,024-ch`) Architecture (`blanker_asic_mezzanine.{kicad_sch,kicad_pcb}`)

Closes the `#281` Defect #6 cross-subsystem HV tension between the `-5,000 V ± 53.3 V` floating ion-column blanker deck (`DESIGN.md` / `S2.2-01`) and `1.8 V` SKY130 CMOS `blanker_tile.v` (`S2.4-01`):

- **Dimensions & Stackup:** `240 × 160 mm`, **`6` copper layers** (`SIG1-GND-SIG2-SIG3-PWR-SIG4`), `1.656 mm` total thickness, UHV low-outgassing **Rogers RO4350B (`ε_r = 3.48`) / Polyimide bondply (`ε_r = 3.40`)**.
- **Exact `src/rtl/blanker_tile.v` Interface (`4×` SKY130 `64-ch` Tiles = `256 ch` / board):**
  - All `13` RTL ports explicitly pinned and physically routed pad-to-pad across `U_TILE0..U_TILE3` (X-staggered `44-pin` ceramic QFP column) and `U_SERDES` (`54-pin` ceramic QFP): `clk`, `rst_n`, `cfg_we`, `cfg_addr[6:0]`, `cfg_data[7:0]`, `start_all`, `count_hit[63:0]`, `blanker_open[63:0]`, `busy_any`, `done_sticky`, `abort_sticky`, `rd_addr[5:0]`, `rd_counted[7:0]`.
- **`5 kV` Galvanic Isolation Barrier (`IEC 61010-1 / IPC-2221B`):**
  - Strictly partitioned primary Earth side (`x ≤ 34 mm`: `2× CF100` UHV flex harness connectors `S2.4-03`) vs. floating `-5 kV` deck (`x ≥ 58 mm`), separated by a `24 mm` copper-free moat across all 6 copper layers and a **`3.5 × 144.0 mm` milled `Edge.Cuts` air-slot**.
  - Wide-body `5 kVrms` reinforced bridging components (`THM15-2423WI-6KV` isolated DC-DC, `AFBR-1624Z/2624Z-5KV` optical control/data transceivers, dedicated `<25 ns` `ACPL-M61L-5KV` fast global override opto-isolator).
  - **Strict Geometric HV DRC:** Air clearance **`16.00 mm`** (`≥ 12.0 mm` req), slot-detour surface creepage **`25.70 mm`** (`≥ 15.0 mm` req), through-board dielectric stress PASS (`0` violations across all segments, vias, pads, and zones).
- **HV Push-Pull Deflector Array & LTCC Interposer (`S2.2-03`):**
  - `16× 16-ch` (`256 ch`) `1.8 V → 27–53.3 V` push-pull deflector level-shifter arrays (`U_HVDRV0..15`) with `50 Ω` damping resistors (`R_DAMP0..15`) fanning out to `J_LTCC_A/B` LTCC/AlN micro-bump ceramic interposer (`S2.2-03` → `S2.2-01` `0.50 mm` MEMS plate).
  - Hard-wired fail-safe global blank-override (`U_ISO_OVRD` → `U_OVRD_GATE` with `10 kΩ` fail-safe pull-down) forces ALL deflector plates to `V_deflect = +53.3 V` (HIGH = beam deflected to dump) on fault or loss of optical carrier.
- **Full Physical Connectivity, Controlled Impedance & Strict EDA Verification:** `63` components (`518` pads), `124` nets, **`routed = 124 / 124` (`100%`)**, **`unconnected_items = 0`**, **`track_dangling_count = 0`**, **`2,250` copper segments**, **`525` vias**, `4` partitioned copper zones, `1` milled air-slot, **`0` ERC errors**, **`0` DRC errors**, **`98 / 98`** `50 Ω SE` / `100 Ω diff` impedance checks PASS (`max error 0.005% ≤ 5.0%`), `min_measured_clearance = 0.1462 mm ≥ 0.127 mm`.

## 2. Live `ngspice-47` HV Switching & Global Override Verification (`blanker_hv_driver.cir`)

Transistor-level native `ngspice-47 -b` simulation (exit `0`, `0` errors, `0` warnings) of the `1.8 V` CMOS override NAND → `5 V` pre-driver → **zero-static-power pulsed-edge high-side CMOS latch** `53.3 V` push-pull stage driving realistic MEMS plate load (`C_plate = 5 pF` + `C_int = 2 pF` + `L_trace = 5 nH` + `R_damp = 50 Ω`), including a `25 ns` `5 kV` opto-isolator propagation delay on the override path:

| Metric | `ngspice-47` Measured | Target / Spec | Status |
| :--- | :---: | :---: | :---: |
| Steady-State Deflector Levels (`V_hi` / `V_lo` / `V_ovrd`) | `53.30 V` / `0.000 V` / `53.30 V` | `53.3 V` / `0 V` / `53.3 V` | **PASS** |
| `10–90%` Rise Time (`0 → 53.3 V`, `7 pF` MEMS load) | **`2.096 ns`** | `< 100 ns` | **PASS** |
| `90–10%` Fall Time (`53.3 → 0 V`, `7 pF` MEMS load) | **`2.223 ns`** | `< 100 ns` | **PASS** |
| End-to-End Global Blank-Override Clamp (incl. `5 kV` opto delay, while `blanker_open` stuck HIGH) | **`51.344 ns`** | `< 200 ns` (`<< 1 µs`) | **PASS** |
| HV Rail Static Dissipation (pulsed-edge latch) | `28.4 µW/ch` (`7.3 mW` / 256 ch) | Minimal UHV heat load | **PASS** |
| Switching Energy / Cycle (`E_hv` vs `C_tot·V² = 19.89 nJ`) | `77.47 nJ/cycle` (incl. HV gate/latch charge) | Bounded | **PASS** |
| `256-ch` Board Total Power (`1 kHz` nominal / `50 kHz` burst) | **`27.34 mW`** / **`1.009 W`** (`1,024-ch @ 1 kHz = 109.3 mW`) | `< 5 W` isolated DC-DC | **PASS** |

## 3. Reproducibility

```bash
PYTHONPATH=.:src python -B hardware/pcb/blanker_asic_mezzanine/build_blanker_mezzanine.py
PYTHONPATH=.:src pytest tests/test_pcb_fpga_blanker_cryo.py -v -p no:cacheprovider
```
