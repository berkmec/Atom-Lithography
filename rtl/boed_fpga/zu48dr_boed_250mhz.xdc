## zu48dr_boed_250mhz.xdc - Xilinx Zynq UltraScale+ RFSoC ZU48DR Timing Constraints
## Target Part: xczu48dr-ffvg1517-2-e (Speed Grade -2E)
## Top Module : boed_top_16ch (internal ZU48DR PS-PL AXI4-Stream IP; physical pin-constrained
##              wrapper provided in boed_top_16ch_tdm_io.v = 48 I/O pins <= 80 carrier / 205 ECP5)
## Epistemic  : Real open-source EDA verified via Icarus Verilog + Verilator + Yosys + nextpnr-ecp5 proxy
##              (no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true)

# ----------------------------------------------------------------------------
# 1. Primary 250.000 MHz System Clock (4.000 ns period, 50% duty cycle)
#    Note: 250 MHz targets Xilinx ZU48DR -2E (DSP48E2); open-source Lattice ECP5
#    proxy P&R operates at a lower speed grade (~40-65 MHz on LFE5U-85F).
# ----------------------------------------------------------------------------
create_clock -name sys_clk -period 4.000 -waveform {0.000 2.000} [get_ports clk]
set_clock_uncertainty -setup 0.080 [get_clocks sys_clk]
set_clock_uncertainty -hold  0.040 [get_clocks sys_clk]

# ----------------------------------------------------------------------------
# 2. Synchronized Reset Bridge Constraint (DO NOT blindly false-path raw rst_n!)
#    boed_q16_core includes an internal 2-FF async-assert / sync-deassert reset
#    bridge (rst_sync_s1 -> rst_sync_s2). Constrain only the async pin -> FF1
#    entry with max_delay while keeping full synchronous recovery timing on rst_sync_n.
# ----------------------------------------------------------------------------
set_property ASYNC_REG TRUE [get_cells -hier -filter {NAME =~ *rst_sync_s1* || NAME =~ *rst_sync_s2*}]
set_max_delay -datapath_only -from [get_ports rst_n] -to [get_cells -hier -filter {NAME =~ *rst_sync_s1*}] 4.000

# ----------------------------------------------------------------------------
# 3. AXI4-Stream & Calibration Register I/O Delay Budgets (RF-DAC/ADC Tile Interface)
# ----------------------------------------------------------------------------
set_input_delay  -clock sys_clk -max 1.200 [get_ports {s_axis_tvalid s_axis_tdata[*] s_axis_tid[*] s_axis_tlast}]
set_input_delay  -clock sys_clk -min 0.250 [get_ports {s_axis_tvalid s_axis_tdata[*] s_axis_tid[*] s_axis_tlast}]
set_input_delay  -clock sys_clk -max 1.500 [get_ports {cfg_* prior_load_*}]
set_input_delay  -clock sys_clk -min 0.200 [get_ports {cfg_* prior_load_*}]

set_output_delay -clock sys_clk -max 1.200 [get_ports {s_axis_tready m_axis_tvalid m_axis_tdata[*] m_axis_tid[*] m_axis_tlast}]
set_output_delay -clock sys_clk -min 0.200 [get_ports {s_axis_tready m_axis_tvalid m_axis_tdata[*] m_axis_tid[*] m_axis_tlast}]
set_output_delay -clock sys_clk -max 1.500 [get_ports {ch_busy_mask[*] ch_sprt_donor_mask[*]}]
set_output_delay -clock sys_clk -min 0.200 [get_ports {ch_busy_mask[*] ch_sprt_donor_mask[*]}]

# ----------------------------------------------------------------------------
# 4. Fully Pipelined Single-Cycle Datapath (Zero Multicycle Waivers)
#    Pass-1 front-end (shift-add -> abs_df reg -> inv_gamma mult reg -> 4-stage
#    boed_lut_rom -> resid -> resid^2 -> dlp -> sat_sub), Pass-2 MAC, and
#    Stage-3 restoring dividers have zero chained 32x32 multipliers.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# 5. DSP48E2 & RAMB36E2 / RAMB18E2 Resource Inference Hints
# ----------------------------------------------------------------------------
set_property USE_DSP yes [get_cells -hier -filter {NAME =~ *u_core*}]
set_property RAM_STYLE block [get_cells -hier -filter {NAME =~ *lp_bank* || NAME =~ *u_lor_lut/rom* || NAME =~ *u_exp_lut/rom*}]
