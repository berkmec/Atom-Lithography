# SKY130 4 K Cryo-CMOS 968-Gate Crossbar MUX RTL (`OBS-143`)

- **BOM Traceability**: `S6.10-03`, `S7.3-01` (`SKY130_4K_CROSSBAR_121G_M0..M7`)
- **Architecture**: 8 daisy-chained SKY130 dies × 121 DC gates/die (11×11 crossbar) = **968 DC gates** for the L=11 surface-code array, matching `hardware/pcb/cryo_cmos_4k_carrier/build_cryo_4k_carrier.py`.
- **Modules**:
  - `sky130_4k_crossbar_121g.v`: Synthesizable 121-gate 1-hot crossbar decoder with 16-bit daisy-chain SPI Mode-0 control, 2-FF CDC + reset synchronizer, cyclic S&H refresh scanner, strict mutual exclusion (`popcount <= 1`), OOB address (`121..127`) rejection, and `OP_ALL_SAFE_ZERO` clamp.
  - `tb_sky130_4k_crossbar_121g.v`: Self-checking 8-die 968-gate daisy-chain testbench verifying all 968 gates, OOB clamp, 121-gate refresh sweep, and global zero clamp.

## Epistemic Status — TRL 2 (Pending 4 K Cryogenic PDK)

- **Digital RTL verified**: `verilator --lint-only -Wall` (0 warnings), `iverilog -g2012 -Wall + vvp` (0 errors across all 968 gates), and `yosys` synthesis (`check -assert`).
- **4 K Cryogenic Signoff NOT Complete (TRL 2)**: At 4 K, SKY130 MOSFETs exhibit threshold voltage shift (`~+0.15–0.25 V`) and kink effect (`kink_ratio` up to `3.84` in `results/exp32/nist_sky130.json`). Standard 300 K TT/SS/FF Liberty corners cannot sign off 4 K silicon; cryogenic BSIM4 re-characterization, analog transmission-gate layout, and full-chip P&R/DRC/LVS remain open pre-tapeout work.
