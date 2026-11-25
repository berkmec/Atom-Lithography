# Atom Lithography Machine — Stage-2 Full 180/180 Engineering Blueprint Summary

**Master Registry:** `hardware/parts_registry.json` (`parts_registry_180_v1.0`)  
**Source BOM:** `research/atom_lithography_machine/BOM_DETAILED.csv` (`v7.0`, `180` rows, `$5,692,800` nominal M3 Full, SHA-256 `a07c717413b49c5b...`)  
**Automated Verifier:** `hardware/verify_full_traceability.py` + `tests/test_full_180_traceability.py`

> **Epistemic Boundary (`M0/M1 DESIGN_ONLY` — Zero Lab Validation):**  
> Every artifact cataloged below is a **preliminary M0/M1 digital engineering design** verified solely with deterministic geometric kernels, EDA linters/simulators/synthesizers (`Verilator 5.055`, `Icarus Verilog 14.0`, `Yosys 0.71+101`), strict KiCad 8 S-expression ERC/DRC + Union-Find physical copper connectivity checkers, and live `ngspice-47` circuit simulations.  
> - `no_lab_measurement = true` — **no** physical hardware has been fabricated, assembled, vacuum-baked, cooled to `20 mK`, or beam-tested.  
> - `no_supplier_quotes = true` — BOM pricing remains parametric/catalog engineering estimates (`Exp128`/`v7.0`).  
> - `no_vendor_vivado_pnr = true` — FPGA RTL utilization is measured via pre-P&R `Yosys` synthesis (`xcup`/`xc7`/`ecp5`), not vendor Vivado post-route timing closure.  
> - `tapeout_done = false` — SKY130 `blanker_tile` ASIC signoff (`S8.2-02`) has open padring/IO and single-pass OpenROAD detailed-reroute ECO work before any MPW shuttle submission.  
> - `iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_safety_assessment = true` — `1oo2D` safety interlock hardware/RTL (`S7.SAFETY-01..06`, `uhv_interlock_fsm.v`, `safety_interlock_1oo2d`) is strictly `DESIGN_ONLY_NOT_CERTIFIED` and requires accredited third-party functional-safety assessment prior to laboratory deployment.

---

## 1. Executive Coverage Matrix (`180 / 180` BOM Traceability)

| Engineering Domain | Coverage | Key Verified Metrics | Master Artifact / Verification Anchor |
| :--- | :---: | :--- | :--- |
| **Unified Per-Part ICDs** | **`180 / 180` (`100.0%`)** | `164` physical solids + `5` non-solid NRE/service/gas + `9` `S8.*` IN-HOUSE SW/RTL/EDA + `2` `$0` superseded pointers (`0` missing, `0` orphans, `0` broken links) | `hardware/icd/parts/<PART_ID>.json`, `hardware/parts_registry.json` |
| **3D Mechanical CAD + Layout-Verified 2D GD&T** | **`164 / 164` solids** | `984` per-part files (`.stl`, `.step` AP214, `.scad`, `.dxf`, layout-verified `.svg`, `.json`); `164/164` watertight (`718,532` tris, `0` boundary/non-manifold edges); hardened 3-ray containment + Möller–Trumbore **`0 / 13,366` global 3D solid clashes**; `2,996.7681 kg` total (`S7.SAFETY = 355.0 kg`, `S9.HPC = 64.0 kg`); `30/30` NIST `0.02–423.15 K` thermal checks; `10/10` GD&T stacks | `hardware/cad_parts/cad_parts_verification.json`, `hardware/cad_parts/master_164_assembly_views.png` |
| **Custom PCBs (100% Routed KiCad 8 + Live `ngspice-47`)** | **`10` PCBs / `8` bundles (`58` BOM IDs)** | **`762 / 762` nets 100% physically routed** (`unrouted = 0`, `unconnected_items = 0`, `track_dangling = 0`, `9,895` segments, `2,538` vias), **`0` ERC / `0` DRC** (strict S-expr, `Z0` ±5%, `5 kV`/`22 kV`/`400 V` milled air-slot clearance/creepage + through-board dielectric withstand), `semi_s2_certified = false` & `iec61508_certified = false` on all `10/10` boards; **`10 / 10` live `ngspice-47`** AC/tran/noise/S-param sims with MNA/analytical parity | `hardware/pcb/*/*_verification.json`, `hardware/pcb/cryo_rf_harness_icd/cryo_rf_thermal_attenuation.json` |
| **Electrical ICDs, Grounding, UPS & Timing** | **`95 / 95` ICDs (`125 / 125` elec union)** | `17 E2 + 35 E3 + 43 E4` per-part pinout/rail/grounding ICDs (`$3,434,800` nom) + `30` `E1` custom PCB parts = **`125/125`** electrical partition; `S7.SAFETY-04` `15 kVA / 13.5 kW / 10 kWh` LFP UPS Tier-1 (`2.533 kW`): **`213.2 min`** Exp150 nominal (`η=0.90`), **`189.6 min`** conservative (`100%` DoD + `350 W` idle loss), **`170.6 min`** conservative (`90%` usable LFP DoD — flagged `< 180 min`, needs `>=10.6 kWh` / `11 kWh` pack or `<=2.35 kW` trim); **`0.0 W`** discrepancy across all `28` `TIER2_SHED` parts (`18,026 W` raw = `12,275 W` Exp150 + `5,401 W` aux + `350 W` overlap) | `hardware/icd/electrical/*.json`, `hardware/icd/electrical/master_electrical_power_ups_budget.json` |
| **Machine-Control & BOED FPGA / ASIC RTL** | **`13` synth `.v` (`32` BOM IDs)** | `rtl/machine_ctrl/` (`7` modules, **`3,212` LOC**): `Verilator 5.055 -Wall` `8/8` (`0` warnings), `Icarus 14.0` `6/6` TBs PASS (`6 ns` interlock override, physical `il_hw_reset_b` two-channel unlock rejecting SW bypass, `r_il_cfg_locked` safety-config write lock, `0`-LSB Q16.16 PID, Q1.15 DDC & `boed_q16_core`), `Yosys 0.71+101` `check -assert` + `xcup` (`15,293` LUT / `11,221` FF / `12` RAMB18E2 / `124` DSP48E2) / `xc7` (`14,296` LUT) / `ecp5` (`14,731` LUT4); plus preserved `rtl/boed_fpga/` (`4` `.v`) & `src/rtl/` (`2` `.v`) | `results/stage2_rtl_verification/rtl_machine_ctrl_audit.json`, `rtl/machine_ctrl/REGMAP.md` |
| **Non-Solid NRE / Service / Gas ICDs** | **`5 / 5`** | `S2.1-02` (SOI DRIE mask NRE), `S2.2-02` (Blanker MEMS/TSV NRE), `S2.3-02` (Mini-lens anodic-bond NRE), `S5.4-02` (SIMS/AFM metrology qualification), `S6.8-03` (`20 L STP` `3He` charge) | `hardware/icd/parts/{S2.1-02,S2.2-02,S2.3-02,S5.4-02,S6.8-03}.json` |
| **IN-HOUSE Software, EDA & SCADA (`S8.*`)** | **`9 / 9`** | Complete `S8.1-01..S8.4-02` traceability including `src/machine_control/scada_telemetry.py` (`S8.4-02`, 32-ch `S1..S9` OPC-UA schema + ISA-18.2 latching alarms + `uhv_interlock_fsm.v` CSR & `auto_recal.py` hooks) and `hardware/eda_flow/openroad_signoff_manifest.json` (`S8.2-02`) | `src/machine_control/scada_telemetry.py`, `hardware/eda_flow/openroad_signoff_manifest.json` |
| **Superseded `$0` Pointers** | **`2 / 2`** | `S6.10-02` → `S5.6-01..04` (in-situ `28Si` LT-MBE capper); `S7.1-04` → `S6.11-01` (ZU48DR Q16.16 BOED-FPGA) | `hardware/icd/parts/{S6.10-02,S7.1-04}.json` |

---

## 2. Subsystem-by-Subsystem 180-Part Breakdown (`S1`–`S9`)

| Sub | Subsystem Title | BOM Rows | Nom Cost (USD) | CAD Solids | CAD Mass (kg) | PCB-Linked | Elec ICDs | RTL-Linked | Non-Solid / SW / Superseded |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `S1` | Ion Source & Deceleration Column | 23 | $484,000 | 23 | 327.35 | 5 | 17 | 3 | — |
| `S2` | MEMS Write Head & 1024-ch Blanker | 18 | $775,500 | 15 | 11.06 | 6 | 6 | 4 | 3 NRE (`S2.1-02, S2.2-02, S2.3-02`) |
| `S3` | Cold-100K IBIC Single-Ion Detector | 14 | $224,000 | 14 | 38.42 | 12 | 5 | 4 | — |
| `S4` | Seismic Isolation, Piezo & Interferometry | 17 | $253,000 | 17 | 449.00 | 1 | 9 | 0 | — |
| `S5` | UHV Chamber, Pumps, 808 nm Laser & MBE | 24 | $433,000 | 23 | 272.99 | 4 | 12 | 4 | 1 Service (`S5.4-02`) |
| `S6` | Cryo, 20 mK DR, 8-Coil Magnet & Readout | 42 | $2,794,100 | 40 | 790.30 | 18 | 25 | 5 | 1 Gas (`S6.8-03`), 1 `$0` (`S6.10-02`) |
| `S7` | Control Racks, Interconnect & Safety | 20 | $349,200 | 19 | 821.00 | 8 | 14 | 8 | 1 `$0` (`S7.1-04`) |
| `S8` | Software, Compiler, RTL & SCADA Stack | 9 | $0 | 0 | 0.00 | 0 | 0 | 4 | 9 IN-HOUSE (`S8.1-01..S8.4-02`) |
| `S9` | Calibration, Spares, Option-Q & Option-HPC | 13 | $380,000 | 13 | 286.65 | 4 | 7 | 0 | — |
| **ALL** | **Total Machine Blueprint (M3 v7.0 Full)** | **180** | **$5,692,800** | **164** | **2,996.77** | **58** | **95** | **32** | **5 Non-Solid + 9 SW + 2 `$0`** |

*(CAD subsystem masses match `hardware/cad_parts/cad_parts_verification.json` (`2,996.7681 kg` total). Electrical union of `58` PCB-linked parts and `95` electrical ICD parts = `125 / 125` electrical BOM parts.)*

---

## 3. Verified 100%-Routed KiCad 8 PCB & Live `ngspice-47` Suite (`10` Boards, `762/762` Nets, `10` Sims)

| Bundle / Board | Stackup & Size | Routed Nets / Segs / Vias | ERC / DRC / Unconn / Dang | Live `ngspice-47` Key Quantitative Verification |
| :--- | :--- | :---: | :---: | :--- |
| `ibic_cold_csa_100k` | 4L RO4350B (`125×105 mm`, `100 K` UHV) | `54/54` · `677` · `192` | `0 / 0 / 0 / 0` | `ENC = 25.234 e⁻ rms` (`≤35 e⁻`), `8` closed 3D guard cages (`0.1076 pF < 0.15 pF`) |
| `ibic_warm_shaper_300k` | 4L FR408HR (`185×135 mm`, `300 K` EMI) | `116/116` · `1,399` · `359` | `0 / 0 / 0 / 0` | `5 keV 31P+` `V_peak = 10.835 mV`, `t_peak = 1.226 µs`, `221/221` `Z0` PASS |
| `ibic_hv_bias_guard` | 4L RO4350B (`110×75 mm`, `100 V` slot) | `21/21` · `164` · `33` | `0 / 0 / 0 / 0` | 3-stage HV filter `-227.86 dB @ 100 kHz`, `0.142 µVrms` integrated noise |
| `fpga_brain_carrier` | 8L FR408HR (`230×170 mm`, `XC7K325T`) | `126/126` · `1,625` · `468` | `0 / 0 / 0 / 0` | `Z_PDN_max = 4.1604 mΩ` (`<10 mΩ`), `5 A` step droop `16.21 mV` (`1.621%`), `104/104` `Z0` PASS |
| `blanker_asic_mezzanine` | 6L RO4350B/PI (`240×160 mm`, `4×64` SKY130) | `124/124` · `2,250` · `525` | `0 / 0 / 0 / 0` | `5 kV` slot clr `16.00 mm` / crp `25.70 mm`; `V_plate = 53.30 V`, `t_rise = 2.096 ns`, override `51.344 ns << 1 µs` |
| `cryo_cmos_4k_carrier` | 4L RO4350B/AlN-CIC (`165×125 mm`, `968` gates) | `53/53` · `653` · `194` | `0 / 0 / 0 / 0` | `4 K/20 mK` RC+Eccosorb `-215.12 dB @ 1 GHz`, `7.523 nV/√Hz`, `P_4K = 13.650 mW ≤ 15.4 mW` |
| `ion_column_hv_dac` | 4L FR408HR (`220×150 mm`, `2`× `5 kV` slots) | `72/72` · `1,104` · `269` | `0 / 0 / 0 / 0` | `5 kV` clr `26.425 mm` / crp `34.125 mm`; `-125.814 dB @ 100 kHz`, `0.147 mVpp`, `1000.001:1` divider, `1.561 µs` |
| `laser_aom_pyrometer_afe` | 4L RO4350B/FR408HR (`185×125 mm`) | `63/63` · `835` · `221` | `0 / 0 / 0 / 0` | 2-color TIA rise `2.636 µs << 10 µs`, integrator `1e-5%` lin err, AOM `2.1538×`, crowbar `0.273 / 4.870 µs` |
| `safety_interlock_1oo2d` *(DESIGN_ONLY_NOT_CERTIFIED)* | 4L FR408HR (`280×175 mm`, `2`× `22 kV` slots) | `74/74` · `910` · `203` | `0 / 0 / 0 / 0` | `22 kV` clr `46.700 mm` / crp `59.631 mm`; `2 MΩ` crowbar `18.286 ms < 50 ms` (`0.363 J`); welded-relay Ch-B `0.824 ms` |
| `cryo_rf_bias_panel` *(+ 3 cryo-RF SPICE decks)* | 4L RO4350B (`170×120 mm`, `400 V` slot) | `59/59` · `278` · `74` | `0 / 0 / 0 / 0` | `S9.4-02` `max |S11| = -39.555 dB` (`4–8 GHz`); `S6.3-04` quench `396.69 V`, `τ = 0.3703 s`, `99.35%`; `S6.7-01` `f_res = 321.5 MHz`, `113.23 dB` iso |
| **TOTAL (`10` Boards)** | **Multi-Layer Controlled-Impedance / HV** | **`762/762` · `9,895` · `2,538`** | **`0 / 0 / 0 / 0`** | **`10 / 10` live `ngspice-47` PASS (`0` err, `0` warn); `semi_s2_certified = False` & `iec61508_certified = False` on `10/10` boards** |

---

## 4. Open Engineering Debt & Pre-Fabrication Gates (Honest Limitations)

1. **No physical prototypes, supplier RFQs, or beam/cryo lab measurements** exist yet (`M0/M1 DESIGN_ONLY`).
2. **Functional safety certification (`S7.SAFETY-01..06`):** `safety_interlock_1oo2d` and `uhv_interlock_fsm.v` enforce `CERTIFIED=0, DESIGN_ONLY_NOT_CERTIFIED=1` (with hardware-enforced physical `il_hw_reset_b` two-channel unlock and `r_il_cfg_locked` safety-parameter lock) and require third-party IEC 61508 SIL-3 / SEMI S2 FMEDA, environmental qualification, and field validation.
3. **Conservative LFP UPS 90% DoD margin (`S7.SAFETY-04`):** While the Exp150 reference formula yields `213.2 min` (`10 kWh × 0.90 / 2.533 kW`) and `100%` DoD including `350 W` continuous online inverter loss yields `189.6 min >= 180 min`, conservative `90%` usable LFP DoD (`9.0 kWh`) yields **`170.6 min`** (`9.4 min` below `180 min`, honestly flagged `tier1_conservative_90pct_dod_meets_180min: false`). Achieving `>= 180 min` under conservative `90%` DoD + `350 W` idle loss requires specifying an **`11 kWh`** (`>= 10.6 kWh`) LFP battery module or trimming Tier-1 outage load to `<= 2.35 kW`.
4. **FPGA post-P&R timing closure:** `rtl/machine_ctrl/` is verified pre-P&R in `Yosys` (`xcup`/`xc7`/`ecp5`) with zero lint warnings and `6/6` Icarus testbenches, but requires vendor Vivado/Radiant place-and-route and hardware board bring-up to close real STA at `100 / 250 MHz`.
5. **SKY130 `blanker_tile` ASIC tape-out (`S8.2-02`):** Historical `Exp76–123` records establish `WNS = +7.21 ns`, `KLayout DRC = 0` (`Exp100` patched v3), `KLayout LVS = MATCH` (`Exp101`), and `li1` density closure (`Exp102`), while full IO padring/sealring integration and a clean single-pass OpenROAD 2024+ detailed-reroute antenna ECO (`Exp123 attempt3/3b`) remain open pre-tapeout items.
6. **Preservation of v7.2 baseline:** All `39` SHA-256-locked v7.2 artifacts (`results/exp151_v7_digital_twin/v7_digital_twin_cert.json`) and all `35` staged v7.2 test files remain untouched and passing alongside the `14` new Stage-2 test suites.
