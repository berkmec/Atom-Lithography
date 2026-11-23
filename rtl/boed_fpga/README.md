# `rtl/boed_fpga/` — Synthesizable IEEE 1364-2005 `Q16.16` BOED-FPGA RTL Core (`Exp149` / `H167`)

Cycle-accurate, bit-exact Verilog-2005 RTL implementation of the **Atom Lithography Machine** `Exp140` 250 MHz Xilinx Zynq UltraScale+ RFSoC (`ZU48DR`) Bayesian Optimal Experimental Design (BOED) spectroscopy accelerator (`src/machine_control/fpga_boed_dsp.py`).

> **Epistemic Disclosure:** `no_external_eda_sim = true`, `no_lab_measurement_rtl = true`. Host verification uses a structural IEEE 1364-2005 synthesis linter, hierarchy port/width checker, and bit-exact cycle-accurate Python co-verifier (`experiments/exp149_boed_verilog_rtl_and_interactive_twin/rtl_verifier149.py`) confirming `0` forbidden constructs, `0` port/width mismatches, `512/512` 0-bit ROM parity, and `64/64` 0-LSB golden-vector parity at `584` cycles (`2.336 µs @ 250 MHz`). Ready for downstream `iverilog`, `verilator`, or Xilinx Vivado `2024.2+` synthesis.

## Module Hierarchy

| File | Role | Target Timing / Capacity |
| :--- | :--- | :--- |
| `boed_lut_rom.v` | Dual-port 512-entry BRAM36 Q16.16 ROM + 8-bit linear interpolator | 2-cycle latency @ 250 MHz |
| `boed_isqrt_cordic.v` | 16-stage pipelined restoring integer `isqrt(32b) -> 16b` | 16-cycle latency, 1 result/cycle, 0 LSB vs `math.isqrt` |
| `boed_q16_core.v` | 4-lane SIMD Q16.16 Stage-2 BOED + 4-cycle Stage-0 SPRT engine | **584 cycles (`2.336 µs`)**, SPRT **4 cycles (`16.0 ns`)** |
| `boed_top_16ch.v` | 16-channel parallel AXI4-Stream (`128b` in / `96b` out) wrapper | 448 DSP48E2 (`10.49%`), 64 BRAM36 (`5.93%`) on ZU48DR |
| `rom_loglik_p0.hex` | 512-word Q16.16 Lorentzian kernel `1/(1+u^2)`, `u in [0, 12]` | 0-bit diff vs `build_lorentzian_lut_q16()` |
| `rom_loglik_p1.hex` | 512-word Q16.16 exponential kernel `exp(-x)`, `x in [0, 16]` | 0-bit diff vs `build_exp_neg_lut_q16()` |
| `golden_vectors.mem` | 64 full end-to-end 256-bit stimulus + expected golden vectors | 0-LSB diff vs `Q1616BOEDCore` |
| `zu48dr_boed_250mhz.xdc` | Vivado `xczu48dr-ffvg1517-2-e` `4.000 ns` clock & multi-cycle constraints | 250 MHz closure target |
| `tb_boed_q16_core.v` | Self-checking IEEE 1364-2005 Verilog testbench | Checks `cycle_count == 584` & 0-LSB outputs |

## External EDA Simulation Commands (When `iverilog` / `vivado` Is Available)

```bash
cd rtl/boed_fpga
iverilog -g2005 -o sim_boed boed_lut_rom.v boed_isqrt_cordic.v boed_q16_core.v tb_boed_q16_core.v
vvp sim_boed
```
