## fpga_machine_ctrl.xdc - Atom Lithography Machine Control FPGA Timing Constraints
## Primary Target Part : Xilinx Zynq UltraScale+ RFSoC ZU48DR (xczu48dr-ffvg1517-2-e)
## Top Module          : fpga_top_machine_ctrl (internal ZU48DR PS-PL top; physical 76-pin
##                       carrier/ECP5 wrapper in fpga_top_carrier_wrap.v <= 80 / 205 I/O)
## Epistemic Status    : Real EDA verified via Verilator + Icarus Verilog + Yosys + nextpnr-ecp5 proxy
##                       (no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true, iec61508_certified=false)

# ----------------------------------------------------------------------------
# 1. Primary 100.000 MHz Machine Control System Clock (10.000 ns period)
#    Hard-wired interlock override budget: <= 3 clocks = <= 30 ns (< 1 us spec)
# ----------------------------------------------------------------------------
create_clock -name sys_clk -period 10.000 -waveform {0.000 5.000} [get_ports clk]
set_clock_uncertainty -setup 0.100 [get_clocks sys_clk]
set_clock_uncertainty -hold  0.050 [get_clocks sys_clk]

# ----------------------------------------------------------------------------
# 2. Synchronized Reset Bridge & 2-FF CDC Input Constraints (OBS-113 / OBS-142)
#    DO NOT blindly set_false_path -from [get_ports rst_n] across all FFs!
#    Every module includes an internal 2-FF async-assert / sync-deassert reset
#    bridge (rst_sync_s1 -> rst_sync_s2) and 2-FF synchronizers on external async
#    inputs (il_ch_a_ok, il_ch_b_ok, il_hw_reset_b, uart_rx, blk_tile_done/abort_in).
#    Constrain raw async pin entry ONLY to stage-1 ASYNC_REG FFs via set_max_delay!
# ----------------------------------------------------------------------------
set_property ASYNC_REG TRUE [get_cells -hier -filter {NAME =~ *rst_sync_s1* || NAME =~ *rst_sync_s2* || NAME =~ *ch_a_s1* || NAME =~ *ch_a_s2* || NAME =~ *ch_b_s1* || NAME =~ *ch_b_s2* || NAME =~ *rst_b_s1* || NAME =~ *rst_b_s2* || NAME =~ *hw_rst_b_s1* || NAME =~ *hw_rst_b_s2* || NAME =~ *rx_sync1* || NAME =~ *rx_sync2*}]
set_max_delay -datapath_only -from [get_ports rst_n] -to [get_cells -hier -filter {NAME =~ *rst_sync_s1*}] 5.000
set_max_delay -datapath_only -from [get_ports {uart_rx il_hw_reset_b}] -to [get_cells -hier -filter {NAME =~ *rx_sync1* || NAME =~ *rst_b_s1* || NAME =~ *hw_rst_b_s1*}] 5.000
set_false_path -to [get_ports {uart_tx uart_rts_n}]

# ----------------------------------------------------------------------------
# 3. Safety Interlock Hard-Wired Fast-Trip Budget (< 1 us total; <= 30 ns FPGA)
# ----------------------------------------------------------------------------
set_input_delay  -clock sys_clk -max 2.000 [get_ports {il_ch_a_ok[*] il_ch_b_ok[*]}]
set_input_delay  -clock sys_clk -min 0.250 [get_ports {il_ch_a_ok[*] il_ch_b_ok[*]}]
set_output_delay -clock sys_clk -max 2.000 [get_ports {safe_blanker_en safe_laser_en safe_hv_en safe_uhv_valve_en safe_ph3_valve_en safe_magnet_en interlock_trip_out safety_indep_trip_out}]
set_output_delay -clock sys_clk -min 0.200 [get_ports {safe_blanker_en safe_laser_en safe_hv_en safe_uhv_valve_en safe_ph3_valve_en safe_magnet_en interlock_trip_out safety_indep_trip_out}]

# ----------------------------------------------------------------------------
# 4. External AXI4-Lite, Blanker Array, AOM PID, SPI DAC & Cryo DDC I/O Budgets
# ----------------------------------------------------------------------------
set_input_delay  -clock sys_clk -max 2.500 [get_ports {ext_axil_awaddr[*] ext_axil_awvalid ext_axil_wdata[*] ext_axil_wstrb[*] ext_axil_wvalid ext_axil_bready ext_axil_araddr[*] ext_axil_arvalid ext_axil_rready}]
set_input_delay  -clock sys_clk -min 0.250 [get_ports {ext_axil_awaddr[*] ext_axil_awvalid ext_axil_wdata[*] ext_axil_wstrb[*] ext_axil_wvalid ext_axil_bready ext_axil_araddr[*] ext_axil_arvalid ext_axil_rready}]
set_output_delay -clock sys_clk -max 2.500 [get_ports {ext_axil_awready ext_axil_wready ext_axil_bresp[*] ext_axil_bvalid ext_axil_arready ext_axil_rdata[*] ext_axil_rresp[*] ext_axil_rvalid}]
set_output_delay -clock sys_clk -min 0.250 [get_ports {ext_axil_awready ext_axil_wready ext_axil_bresp[*] ext_axil_bvalid ext_axil_arready ext_axil_rdata[*] ext_axil_rresp[*] ext_axil_rvalid}]

set_input_delay  -clock sys_clk -max 2.500 [get_ports {blk_tile_done_in[*] blk_tile_abort_in[*] aom_ext_sample_valid aom_ext_meas_q16[*] aom_ext_temp_meas_k[*] ddc_adc_valid ddc_adc_sample[*] ddc_mf_weight[*] ddc_m_axis_tready}]
set_input_delay  -clock sys_clk -min 0.250 [get_ports {blk_tile_done_in[*] blk_tile_abort_in[*] aom_ext_sample_valid aom_ext_meas_q16[*] aom_ext_temp_meas_k[*] ddc_adc_valid ddc_adc_sample[*] ddc_mf_weight[*] ddc_m_axis_tready}]
set_output_delay -clock sys_clk -max 2.500 [get_ports {blk_tile_sel[*] blk_tile_sclk blk_tile_sdata blk_tile_latch_n blk_frame_latch_n blk_tile_beam_en[*] blk_safe_blanked aom_rf_en aom_drive_q16[*] spi_cs_n spi_sclk spi_mosi spi_ldac_n hv_clr_n ddc_adc_ready ddc_m_axis_tvalid ddc_m_axis_tdata[*] ddc_m_axis_tid[*] ddc_m_axis_tlast ddc_qubit_state_mask[*]}]
set_output_delay -clock sys_clk -min 0.200 [get_ports {blk_tile_sel[*] blk_tile_sclk blk_tile_sdata blk_tile_latch_n blk_frame_latch_n blk_tile_beam_en[*] blk_safe_blanked aom_rf_en aom_drive_q16[*] spi_cs_n spi_sclk spi_mosi spi_ldac_n hv_clr_n ddc_adc_ready ddc_m_axis_tvalid ddc_m_axis_tdata[*] ddc_m_axis_tid[*] ddc_m_axis_tlast ddc_qubit_state_mask[*]}]

# ----------------------------------------------------------------------------
# 5. Pipelined DSP & BRAM Resource Inference Hints (Zero Multicycle Waivers)
#    All DSP multiplies in aom_pid_ctrl, cryo_mux_ddc_ctrl, and boed_q16_core
#    are isolated in dedicated pipeline stages with zero combinational '/'.
# ----------------------------------------------------------------------------
set_property USE_DSP yes [get_cells -hier -filter {NAME =~ *u_aom_pid* || NAME =~ *u_cryo_ddc* || NAME =~ *u_boed_core*}]
set_property RAM_STYLE block [get_cells -hier -filter {NAME =~ *lp_bank* || NAME =~ *u_lor_lut/rom* || NAME =~ *u_exp_lut/rom*}]
