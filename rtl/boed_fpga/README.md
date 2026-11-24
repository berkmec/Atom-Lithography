# `rtl/boed_fpga/` — Real-EDA Verified Synthesizable `Q16.16` BOED-FPGA Verilog RTL Core (`Exp149` / `H167`)

Cycle-accurate, bit-exact Verilog-2005 RTL implementation of the **Atom Lithography Machine** `Exp140` 250 MHz Xilinx Zynq UltraScale+ RFSoC (`ZU48DR`) Bayesian Optimal Experimental Design (BOED) spectroscopy accelerator (`src/machine_control/fpga_boed_dsp.py`).

> **Epistemic Disclosure:** **`no_external_eda_sim = false`** (verified directly with real **Verilator 5.055 `--lint-only -Wall`**, **Icarus Verilog 14.0 `-g2012 -Wall` + `vvp`**, and **Yosys 0.71+101** `check -assert` + `synth_xilinx -family xcup` / `synth_xilinx -family xc7` / `synth_ecp5`!). **`no_vendor_vivado_pnr = true`**, **`no_lab_measurement_rtl = true`** (Yosys cell counts are real pre-P&R technology-mapped counts; vendor Vivado place-and-route timing closure and physical RFSoC board measurements are pending).

## Module Hierarchy

| File | Role | Verification Status |
| :--- | :--- | :--- |
| `boed_lut_rom.v` | Dual-port 512-entry reset-less BRAM Q16.16 ROM + 8-bit linear interpolator | 2-cycle latency, infers `1× RAMB18E2` / `DP16KD`, `0` Verilator `-Wall` warnings |
| `boed_isqrt_cordic.v` | 16-stage pipelined restoring integer `isqrt(32b) -> 16b` | 16-cycle latency, 1 result/cycle, 0 LSB across 13 `vvp` corners + 1,000 Python vectors |
| `boed_q16_core.v` | 4-lane SIMD Q16.16 Stage-2 BOED + 4-cycle Stage-0 SPRT + 3 parallel bit-serial restoring dividers (`0` combinational `/` operators) | **584 cycles (`2.336 µs @ 250 MHz`)**, SPRT **4 cycles (`16.0 ns`)**, **64/64 `vvp` vectors @ 0 LSB** |
| `boed_top_16ch.v` | 16-channel parallel AXI4-Stream (`128b` in / `96b` out) wrapper + priority arbiter | 4 concurrent channels + backpressure + SPRT verified in `vvp` @ **0 LSB / 584 cycles** |
| `rom_loglik_p0.hex` | 512-word Q16.16 Lorentzian kernel `1/(1+u^2)`, `u in [0, 12]` | 0-bit diff vs `build_lorentzian_lut_q16()` |
| `rom_loglik_p1.hex` | 512-word Q16.16 exponential kernel `exp(-x)`, `x in [0, 16]` | 0-bit diff vs `build_exp_neg_lut_q16()` |
| `golden_vectors.mem` | 64 diverse 288-bit vectors (8 physical regimes × 8 sequential updates) | 0-LSB match in `vvp` (`mu_off_q8`, `std_q4`, `next_probe_off_q8`, `cycle_count=584`) |
| `zu48dr_boed_250mhz.xdc` | Vivado `xczu48dr-ffvg1517-2-e` `4.000 ns` single-cycle clock constraints | Zero multicycle path waivers required |
| `tb_boed_q16_core.v` | Self-checking testbench (64 diverse vectors + 8 SPRT shots + 13 `isqrt` corners) | `PASS` (`0` errors, `0` LSB, `584` cycles) |
| `tb_boed_top_16ch.v` | 16-channel AXI4-Stream multi-channel + backpressure + SPRT testbench | `PASS` (`4/4` concurrent channels @ `0` LSB / `584` cycles) |
| `Makefile` | Portable rootless EDA runner (`lint`, `sim`, `synth-xcup`, `synth-xc7`, `synth-ecp5`, `synth-top16`) | Resolves `PATH` or `$HOME/.local/oss-cad-suite/bin` |

## Real Measured Yosys Pre-P&R Synthesis Results

| Target | Command | LUTs (+SRL) | FFs | BRAM Blocks (`BRAM36-eq`) | DSP / MULT | ZU48DR Fit |
| :--- | :--- | ---: | ---: | ---: | ---: | :---: |
| `boed_q16_core` (`xcup`) | `synth_xilinx -family xcup` | `6,357` | `3,690` | `12 RAMB18E2` (`6.0`) | `99 DSP48E2` | `1.49%` LUT / `2.32%` DSP |
| `boed_top_16ch` (`xcup`) | `synth_xilinx -family xcup` | `102,886` | `59,157` | `192 RAMB18E2` (`96.0`) | `1,584 DSP48E2` | **`24.19%` LUT / `6.96%` FF / `8.89%` BRAM / `37.08%` DSP** |
| `boed_q16_core` (`xc7`) | `synth_xilinx -family xc7` | `5,467` | `3,080` | `12 RAMB18E1` (`6.0`) | `99 DSP48E1` | 7-Series reference |
| `boed_q16_core` (`ecp5`) | `synth_ecp5` | `3,871` (`LUT4`) | `4,448` (`TRELLIS_FF`) | `12 DP16KD` (`6.0`) | `106 MULT18X18D` | Lattice ECP5 reference |

> **Pre-P&R vs Analytical Vivado Estimate:** Yosys pre-P&R maps full 32×32 Q16.16 multiplies unshared across `99 DSP48E2/core` (`1,584` for 16ch = `37.08%` of ZU48DR's `4,272`), whereas `fpga_boed_dsp.py`'s analytical estimate (`28/core`, `448` total = `10.49%`) assumed time-shared / Vivado-packed DSPs. Both fit comfortably inside ZU48DR (`0.0 W` cryogenic heat load).

## Reproducible EDA Commands

```bash
cd rtl/boed_fpga
make lint          # Verilator --lint-only -Wall on boed_q16_core & boed_top_16ch
make sim           # Icarus Verilog -g2012 -Wall + vvp on tb_boed_q16_core & tb_boed_top_16ch
make synth-xcup    # Yosys synth_xilinx -family xcup on boed_q16_core
make synth-xc7     # Yosys synth_xilinx -family xc7 on boed_q16_core
make synth-ecp5    # Yosys synth_ecp5 on boed_q16_core
make synth-top16   # Yosys synth_xilinx -family xcup on boed_top_16ch
```
