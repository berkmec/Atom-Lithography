## fpga_machine_ctrl.xdc - Atom Lithography Machine Control FPGA Timing Constraints
## Primary Target Part : Xilinx Zynq UltraScale+ RFSoC ZU48DR (xczu48dr-ffvg1517-2-e)
## Top Module          : fpga_top_machine_ctrl (Unified Machine Control + BOED Q16 Core)
## Epistemic Status    : Real EDA pre-P&R verified via Verilator + Icarus Verilog + Yosys
##                       (no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true, iec61508_certified=false)

# ----------------------------------------------------------------------------
# 1. Primary 100.000 MHz Machine Control System Clock (10.000 ns period)
#    Hard-wired interlock override budget: <= 2 clocks = <= 20 ns (< 1 us spec)
# ----------------------------------------------------------------------------
create_clock -name sys_clk -period 10.000 -waveform {0.000 5.000} [get_ports clk]
set_clock_uncertainty -setup 0.100 [get_clocks sys_clk]
set_clock_uncertainty -hold  0.050 [get_clocks sys_clk]

# ----------------------------------------------------------------------------
# 2. Asynchronous Reset & External Human/Sensor Input Constraints
# ----------------------------------------------------------------------------
set_false_path -from [get_ports rst_n]
set_false_path -from [get_ports {uart_rx il_hw_reset_b}]
set_false_path -to   [get_ports uart_tx]

# ----------------------------------------------------------------------------
# 3. Safety Interlock Hard-Wired Fast-Trip Budget (< 1 us total; <= 20 ns FPGA)
# ----------------------------------------------------------------------------
set_input_delay  -clock sys_clk -max 2.000 [get_ports {il_ch_a_ok[*] il_ch_b_ok[*]}]
set_input_delay  -clock sys_clk -min 0.250 [get_ports {il_ch_a_ok[*] il_ch_b_ok[*]}]
set_output_delay -clock sys_clk -max 2.000 [get_ports {safe_blanker_en safe_laser_en safe_hv_en safe_uhv_valve_en safe_ph3_valve_en safe_magnet_en interlock_trip_out}]
set_output_delay -clock sys_clk -min 0.200 [get_ports {safe_blanker_en safe_laser_en safe_hv_en safe_uhv_valve_en safe_ph3_valve_en safe_magnet_en interlock_trip_out}]

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
# 5. Single-Cycle Registered Timing Closure (Zero Multicycle Waivers Required)
#    All DSP multiplies in aom_pid_ctrl, cryo_mux_ddc_ctrl, and boed_q16_core
#    are fully pipelined with zero combinational '/' division operators.
# ----------------------------------------------------------------------------
set_property USE_DSP yes [get_cells -hier -filter {NAME =~ *u_aom_pid* || NAME =~ *u_cryo_ddc* || NAME =~ *u_boed_core*}]
set_property RAM_STYLE block [get_cells -hier -filter {NAME =~ *lp_bank* || NAME =~ *u_lor_lut/rom* || NAME =~ *u_exp_lut/rom*}]
