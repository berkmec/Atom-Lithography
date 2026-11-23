## zu48dr_boed_250mhz.xdc - Xilinx Zynq UltraScale+ RFSoC ZU48DR Timing Constraints
## Target Part: xczu48dr-ffvg1517-2-e (Speed Grade -2E)
## Top Module : boed_top_16ch (16 parallel Q16.16 BOED-FPGA engines, 584 cycles = 2.336 us @ 250 MHz)
## Epistemic  : {Model} synthesis constraint file (no Vivado run on host; ready for Vivado 2024.2+)

# ----------------------------------------------------------------------------
# 1. Primary 250.000 MHz System Clock (4.000 ns period, 50% duty cycle)
# ----------------------------------------------------------------------------
create_clock -name sys_clk -period 4.000 -waveform {0.000 2.000} [get_ports clk]
set_clock_uncertainty -setup 0.080 [get_clocks sys_clk]
set_clock_uncertainty -hold  0.040 [get_clocks sys_clk]

# ----------------------------------------------------------------------------
# 2. Synchronous Reset False Path (debounced PS/PL reset synchronizer upstream)
# ----------------------------------------------------------------------------
set_false_path -from [get_ports rst_n]

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
# 4. Multi-Cycle Path Relaxations for 32-Cycle Stage-3 Moment Divider
#    (Divider result latched cleanly on S_POST phase_cnt == 32; 32 cycles available)
# ----------------------------------------------------------------------------
set_multicycle_path -setup 16 -from [get_cells -hier -filter {NAME =~ *acc_m1_reg* || NAME =~ *acc_m2_reg* || NAME =~ *acc_z_reg*}] \
                              -to   [get_cells -hier -filter {NAME =~ *post_mu_off_q8_reg* || NAME =~ *post_mean_b_q8_reg* || NAME =~ *post_ex2_q16_reg*}]
set_multicycle_path -hold  15 -from [get_cells -hier -filter {NAME =~ *acc_m1_reg* || NAME =~ *acc_m2_reg* || NAME =~ *acc_z_reg*}] \
                              -to   [get_cells -hier -filter {NAME =~ *post_mu_off_q8_reg* || NAME =~ *post_mean_b_q8_reg* || NAME =~ *post_ex2_q16_reg*}]

# ----------------------------------------------------------------------------
# 5. DSP48E2 & RAMB36E2 Resource Hints (ZU48DR: 448/4272 DSP48E2, 64/1080 BRAM36)
# ----------------------------------------------------------------------------
set_property USE_DSP yes [get_cells -hier -filter {NAME =~ *u_core*}]
set_property RAM_STYLE block [get_cells -hier -filter {NAME =~ *lp_bank* || NAME =~ *u_lor_lut/rom_reg* || NAME =~ *u_exp_lut/rom_reg*}]
