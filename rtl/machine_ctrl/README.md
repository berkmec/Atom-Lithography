# `rtl/machine_ctrl/` — Unified Atom Lithography Machine Control FPGA RTL Suite

Synthesizable Verilog-2005 hardware control suite (`3,212` LOC across 7 core modules + 6 self-checking testbenches) implementing the full digital machine-control brain for the **Atom Lithography Machine** (`fpga_top_machine_ctrl`), integrating the existing read-only `../boed_fpga/boed_q16_core.v` accelerator with five dedicated real-time hardware controllers, a UART 8N1 / AXI4-Lite CSR bridge, and a non-bypassable hard-wired safety override bus.

> **Epistemic Disclosure:**
> - **`no_external_eda_sim = false`** — Verified directly with real open-source EDA tools: **Verilator 5.055 `--lint-only -Wall`** (`0` warnings, `0` errors, `0` pragmas), **Icarus Verilog 14.0 `-g2012 -Wall` + `vvp`** (`6/6` testbenches PASS, `0` compile warnings, `0` errors, `0`-LSB Python parity), and **Yosys 0.71+101** (`check -assert` + full pre-P&R technology mapping for `xcup`, `xc7`, and `ecp5`).
> - **`no_vendor_vivado_pnr = true`** — Yosys cell counts are real pre-P&R technology-mapped primitives; vendor Vivado place-and-route timing closure is pending.
> - **`no_lab_measurement_rtl = true`** — No physical FPGA board or laboratory hardware measurements have been performed.
> - **`iec61508_certified = false`**, **`semi_s2_certified = false`** — Read-only epistemic CSRs (`0x0008`, `0x011C`) hardwire `CERTIFIED = 0` and `DESIGN_ONLY_NOT_CERTIFIED = 1`.

---

## Module Hierarchy & BOM Traceability

| Module | LOC | BOM Part IDs | Function & Verified Real-EDA Gate |
| :--- | ---: | :--- | :--- |
| `blanker_array_ctrl.v` | `331` | `S2.2-01, S2.4-01/02, S3.3-01/02` | `32×32 = 1,024`-ch (`16×64` tile) serializer, `1024`-bit pattern & dead-channel mask RAMs, signed `(dx_pitch, dy_pitch)` step-and-stitch, sticky tile done/abort aggregator, hard-wired `interlock_blank_force` clamp (**`6 ns`** comb+sync latch, `<= 20 ns`, strictly `< 1 µs`) |
| `uhv_interlock_fsm.v` | `338` | `S5.5-04, S7.4-04, S7.SAFETY-01..06` | True **1oo2D** dual-channel (`ch_a_ok[7:0]`, `ch_b_ok[7:0]`) fail-safe voting FSM (UHV, Class-4 laser, ODH `O2<19.5%`, PH3 L1/L2, HV, quench, E-Stop), cross-channel discrepancy monitor, hardware watchdog heartbeat, de-energize-to-trip enables (**`<= 16 ns`** max trip), staged safe-dwell dual-reset unlock, read-only `DESIGN_ONLY_NOT_CERTIFIED` CSR |
| `aom_pid_ctrl.v` | `304` | `S5.3-03, S5.5-01/03, S1.4-03` | Bit-exact `Q16.16` anti-windup discrete PID (back-calculation anti-windup, filtered D-on-measurement, `[0.65, 1.40]` clamp, 16-tap dead-time shift register, pyrometer trim, hardwired `T >= 1687 K` Si melt abort → zero drive, **`0` LSB** vs Python reference across 24 steps) |
| `spi_dac_hv_ctrl.v` | `278` | `S1.2-03, S1.3-03, S2.3-04, S3.2-02, S6.7-02, S6.10-03/04` | Synchronized 8-channel 20-bit SPI Mode-0 DAC master (`24`-bit `{0, ch[2:0], code[19:0]}` frames), programmable `SCLK` divider, simultaneous `spi_ldac_n` strobe, hardware `hv_safe_clamp` immediate `hv_clr_n=0` + autonomous 8-ch `20'h00000` zero-override SPI burst |
| `cryo_mux_ddc_ctrl.v` | `426` | `S6.6-06, S6.11-01` | Parameterizable multi-tone NCO IQ DDC (`N_CH = 8` default, verified up to `32` time-multiplexed tones), exact 256-entry midpoint-symmetric Q1.15 quarter-wave sin/cos LUT ROM, signed IQ mixer, boxcar + matched-filter integrator, rotated-axis threshold discriminator, AXI4-Stream master output (**`0` LSB** vs Python Q1.15 reference) |
| `uart_axi_regmap.v` | `448` | `S3.3-01/04, S7.2-02, S8.4-02` | Full UART 8N1 RX/TX (`115,200 baud` default @ `100 MHz`) binary framed bridge driving internal AXI4-Lite Master (`'W'` 7B write / `'R'` 3B read) |
| `fpga_top_machine_ctrl.v` | `1,087` | Unified Top + `../boed_fpga/boed_q16_core.v` (`S8.3-03`) | Integrates all 6 controllers + read-only `boed_q16_core` (`584` cycles, **`0` LSB** Exp149 Golden V0 parity on `0x063C/0x0640/0x0644`) + 2:1 UART/External AXI4-Lite CSR map (`0x0000`–`0x06FF`) + strict physical `il_hw_reset_b` Channel-B interlock reset (zero SW bypass) + hardware `r_il_cfg_locked` safety-timer write lock + DDC→BOED SPRT AXI4-Stream autofeed + hard-wired simultaneous interlock override bus (**`6 ns`** trip across blanker/AOM/HV) |

**Total New Synthesizable RTL:** **`3,212` LOC** (excluding read-only `../boed_fpga/` and testbenches; `0` combinational `/` operators, `0` latches, `0` Verilator pragmas).

---

## Real Measured Yosys Pre-P&R Synthesis Results (`fpga_top_machine_ctrl`)

Full unified top-level (all 6 new machine-control modules **plus** instantiated `boed_q16_core`):

| Target | Yosys Command | LUTs (+SRL) | FFs | BRAM Blocks (`BRAM36-eq`) | DSP / MULT | ZU48DR Fit (`xcup`) |
| :--- | :--- | ---: | ---: | ---: | ---: | :---: |
| **`xcup`** | `synth_xilinx -family xcup -top fpga_top_machine_ctrl` | **`15,293`** (`15,165` + `128` SRL) | **`11,221`** | **`12 RAMB18E2`** (`6.0`) | **`124 DSP48E2`** | **`3.60%` LUT / `1.32%` FF / `0.56%` BRAM / `2.90%` DSP** |
| **`xc7`** | `synth_xilinx -family xc7 -top fpga_top_machine_ctrl` | **`14,296`** (`14,168` + `128` SRL) | **`10,517`** | **`12 RAMB18E1`** (`6.0`) | **`124 DSP48E1`** | 7-Series reference |
| **`ecp5`** | `synth_ecp5 -top fpga_top_machine_ctrl` | **`14,731`** (`LUT4`) | **`11,973`** (`TRELLIS_FF`) | **`12 DP16KD`** (`6.0`) | **`131 MULT18X18D`** | Lattice ECP5 reference |

Saved machine-readable audit artifacts: `results/stage2_rtl_verification/{yosys_xcup_stat,yosys_xc7_stat,yosys_ecp5_stat,rtl_machine_ctrl_audit}.json`.

---

## Verification & Reproducible Commands

See [`REGMAP.md`](REGMAP.md) for the complete `0x0000`–`0x06FF` bit-level CSR map and UART framing protocol.

```bash
cd rtl/machine_ctrl
make lint          # Verilator --lint-only -Wall across all 7 modules (8ch & 32ch DDC) + top (0 warnings)
make sim           # Icarus Verilog -g2012 -Wall + vvp across all 6 self-checking testbenches (0 errors)
make check         # Yosys hierarchy + proc + opt + check -assert (0 latches, 0 comb loops)
make synth-all     # Real Yosys pre-P&R synthesis for xcup, xc7, and ecp5

# Full Python + Real-EDA pytest suite (includes 0-LSB Python parity for AOM PID & Cryo DDC):
pytest tests/test_rtl_machine_ctrl.py -v
```
