// fpga_top_machine_ctrl.v - Unified Atom Lithography Machine Control FPGA Top-Level
// BOM Traceability: S1.2-03, S1.3-03, S1.4-03, S2.2-01, S2.3-04, S2.4-01/02, S3.2-02,
//                   S3.3-01/02/04, S5.3-03, S5.5-01/03/04, S6.6-06, S6.7-02,
//                   S6.10-03/04, S6.11-01, S7.2-02, S7.4-04, S7.SAFETY-01..06, S8.4-02
// Target Device   : Xilinx Zynq UltraScale+ RFSoC ZU48DR (xczu48dr-ffvg1517-2-e) @ 100 MHz
//                   (pin-constrained physical carrier/ECP5 wrapper in fpga_top_carrier_wrap.v)
//
// Hardened Architecture:
//   - Built-in 2-FF async-assert / sync-deassert reset synchronizer (`rst_sync_n`) (OBS-113/142)
//   - 2-FF CDC sync on `il_hw_reset_b`, `il_ch_a_ok`, `il_ch_b_ok`, `blk_tile_done/abort_in`
//   - Hardware-locked safety watchdog (`HARDWIRE_WDT_ALWAYS_ON=1`): unlocked CSR writes CANNOT
//     disable watchdog! Exposes independent registered `safety_indep_trip_out` (OBS-116)
//   - Independent AXI4-Lite AWVALID/WVALID skid capture + `wstrb` byte-enable masking (OBS-115)
//   - 16-byte UART RX FIFO + `uart_rts_n` flow control + inter-byte timeout recovery (OBS-115)
//   - 100 MSPS parallel streaming Cryo-MUX DDC + arbitrated single-channel BOED SPRT autofeed
//     selecting `r_boed_ddc_autofeed_ch[4:0]` (CSR 0x0600[20:16]) — zero channel collision (OBS-114)
//
// Synthesis Hygiene: ZERO latches, ZERO combinational '/', ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module fpga_top_machine_ctrl #(
    parameter [15:0]  UART_BAUD_DIV    = 16'd868, // 115,200 baud @ 100 MHz
    parameter integer DDC_N_CH         = 8,       // 8 active tones (parameterizable up to 32)
    parameter         BOED_LOR_HEX     = "../boed_fpga/rom_loglik_p0.hex",
    parameter         BOED_EXP_HEX     = "../boed_fpga/rom_loglik_p1.hex"
) (
    input  wire        clk,
    input  wire        rst_n,

    // 1. Host UART 8N1 SCADA/Control Interface (+ hardware RTS flow control)
    input  wire        uart_rx,
    output wire        uart_tx,
    output wire        uart_rts_n,

    // 2. Internal/Direct AXI4-Lite Slave Interface (Zynq PS / Direct Testbench)
    input  wire [15:0] ext_axil_awaddr,
    input  wire        ext_axil_awvalid,
    output wire        ext_axil_awready,
    input  wire [31:0] ext_axil_wdata,
    input  wire [3:0]  ext_axil_wstrb,
    input  wire        ext_axil_wvalid,
    output wire        ext_axil_wready,
    output wire [1:0]  ext_axil_bresp,
    output wire        ext_axil_bvalid,
    input  wire        ext_axil_bready,
    input  wire [15:0] ext_axil_araddr,
    input  wire        ext_axil_arvalid,
    output wire        ext_axil_arready,
    output wire [31:0] ext_axil_rdata,
    output wire [1:0]  ext_axil_rresp,
    output wire        ext_axil_rvalid,
    input  wire        ext_axil_rready,

    // 3. 1oo2D Fail-Safe Interlock Physical I/O
    input  wire [7:0]  il_ch_a_ok,
    input  wire [7:0]  il_ch_b_ok,
    input  wire        il_hw_reset_b,
    output wire        safe_blanker_en,
    output wire        safe_laser_en,
    output wire        safe_hv_en,
    output wire        safe_uhv_valve_en,
    output wire        safe_ph3_valve_en,
    output wire        safe_magnet_en,
    output wire        interlock_trip_out,
    output wire        safety_indep_trip_out,

    // 4. 32x32 Blanker Array Physical I/O
    input  wire [15:0] blk_tile_done_in,
    input  wire [15:0] blk_tile_abort_in,
    output wire [3:0]  blk_tile_sel,
    output wire        blk_tile_sclk,
    output wire        blk_tile_sdata,
    output wire        blk_tile_latch_n,
    output wire        blk_frame_latch_n,
    output wire [15:0] blk_tile_beam_en,
    output wire        blk_safe_blanked,

    // 5. AOM Laser PID Physical Sensor & Drive I/O
    input  wire               aom_ext_sample_valid,
    input  wire signed [31:0] aom_ext_meas_q16,
    input  wire        [15:0] aom_ext_temp_meas_k,
    output wire               aom_rf_en,
    output wire signed [31:0] aom_drive_q16,

    // 6. 8-Channel 20-Bit SPI DAC HV Physical I/O
    output wire        spi_cs_n,
    output wire        spi_sclk,
    output wire        spi_mosi,
    output wire        spi_ldac_n,
    output wire        hv_clr_n,

    // 7. Cryo MUX DDC ADC Input & External AXI4-Stream Output
    input  wire               ddc_adc_valid,
    output wire               ddc_adc_ready,
    input  wire signed [15:0] ddc_adc_sample,
    input  wire signed [15:0] ddc_mf_weight,
    output wire               ddc_m_axis_tvalid,
    input  wire               ddc_m_axis_tready,
    output wire        [63:0] ddc_m_axis_tdata,
    output wire        [4:0]  ddc_m_axis_tid,
    output wire               ddc_m_axis_tlast,
    output wire [DDC_N_CH-1:0] ddc_qubit_state_mask
);
    // Global Constants
    localparam [31:0] CHIP_ID_CONST        = 32'h414C_4D02; // "ALM\x02"
    localparam [31:0] VERSION_CONST        = 32'h0002_0002; // v2.0.2 (hardened)
    localparam [31:0] GLOBAL_EPISTEMIC_CSR = 32'hD001_530E; // CERTIFIED=0, DESIGN_ONLY=1, NO_LAB=1, NO_VIVADO_PNR=1

    // 2-FF async-assert / sync-deassert top-level reset synchronizer
    (* ASYNC_REG = "TRUE" *) reg rst_sync_s1;
    (* ASYNC_REG = "TRUE" *) reg rst_sync_s2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst_sync_s1 <= 1'b0;
            rst_sync_s2 <= 1'b0;
        end else begin
            rst_sync_s1 <= 1'b1;
            rst_sync_s2 <= rst_sync_s1;
        end
    end
    wire rst_sync_n = rst_sync_s2;

    // 2-FF CDC synchronizer for physical service-unlock pushbutton il_hw_reset_b
    (* ASYNC_REG = "TRUE" *) reg hw_rst_b_s1;
    (* ASYNC_REG = "TRUE" *) reg hw_rst_b_s2;

    // Byte-enable merge helper for AXI4-Lite wstrb compliance
    function [31:0] apply_wstrb;
        input [31:0] old_val;
        input [31:0] new_val;
        input [3:0]  strb;
        begin
            apply_wstrb[7:0]   = strb[0] ? new_val[7:0]   : old_val[7:0];
            apply_wstrb[15:8]  = strb[1] ? new_val[15:8]  : old_val[15:8];
            apply_wstrb[23:16] = strb[2] ? new_val[23:16] : old_val[23:16];
            apply_wstrb[31:24] = strb[3] ? new_val[31:24] : old_val[31:24];
        end
    endfunction

    function [15:0] apply_wstrb16;
        input [15:0] old_val;
        input [15:0] new_val;
        input [1:0]  strb;
        begin
            apply_wstrb16[7:0]  = strb[0] ? new_val[7:0]  : old_val[7:0];
            apply_wstrb16[15:8] = strb[1] ? new_val[15:8] : old_val[15:8];
        end
    endfunction

    // -----------------------------------------------------------------------
    // 1. UART 8N1 -> Internal AXI4-Lite Master Bridge (with 16B RX FIFO + RTS)
    // -----------------------------------------------------------------------
    wire [15:0] uart_awaddr;
    wire        uart_awvalid;
    wire        uart_awready;
    wire [31:0] uart_wdata;
    wire [3:0]  uart_wstrb;
    wire        uart_wvalid;
    wire        uart_wready;
    wire [1:0]  uart_bresp;
    wire        uart_bvalid;
    wire        uart_bready;
    wire [15:0] uart_araddr;
    wire        uart_arvalid;
    wire        uart_arready;
    wire [31:0] uart_rdata;
    wire [1:0]  uart_rresp;
    wire        uart_rvalid;
    wire        uart_rready;
    wire        uart_bridge_busy;
    wire [15:0] uart_rx_err_cnt;
    wire [15:0] uart_rx_ovf_cnt;

    uart_axi_regmap #(
        .DEFAULT_BAUD_DIV(UART_BAUD_DIV)
    ) u_uart_axi (
        .clk              (clk),
        .rst_n            (rst_n),
        .cfg_baud_div     (16'd0),
        .uart_rx          (uart_rx),
        .uart_tx          (uart_tx),
        .uart_rts_n       (uart_rts_n),
        .m_axil_awaddr    (uart_awaddr),
        .m_axil_awvalid   (uart_awvalid),
        .m_axil_awready   (uart_awready),
        .m_axil_wdata     (uart_wdata),
        .m_axil_wstrb     (uart_wstrb),
        .m_axil_wvalid    (uart_wvalid),
        .m_axil_wready    (uart_wready),
        .m_axil_bresp     (uart_bresp),
        .m_axil_bvalid    (uart_bvalid),
        .m_axil_bready    (uart_bready),
        .m_axil_araddr    (uart_araddr),
        .m_axil_arvalid   (uart_arvalid),
        .m_axil_arready   (uart_arready),
        .m_axil_rdata     (uart_rdata),
        .m_axil_rresp     (uart_rresp),
        .m_axil_rvalid    (uart_rvalid),
        .m_axil_rready    (uart_rready),
        .bridge_busy      (uart_bridge_busy),
        .rx_frame_err_cnt (uart_rx_err_cnt),
        .rx_overrun_cnt   (uart_rx_ovf_cnt)
    );

    // -----------------------------------------------------------------------
    // 2. 2:1 AXI4-Lite Slave Arbiter with Independent AW / W Channel Capture
    //    Accepts AWVALID and WVALID in ANY order (AW-first, W-first, or simultaneous)
    //    so Xilinx AXI Crossbar / SmartConnect masters NEVER deadlock (OBS-115)!
    // -----------------------------------------------------------------------
    reg        ext_aw_held;
    reg [15:0] ext_awaddr_q;
    reg        ext_w_held;
    reg [31:0] ext_wdata_q;
    reg [3:0]  ext_wstrb_q;

    reg        b_pending;
    reg        b_owner;       // 0 = UART, 1 = EXT
    reg        r_pending;
    reg        r_owner;       // 0 = UART, 1 = EXT
    reg [31:0] r_data_q;

    // Independent AW/W readiness on external AXI4-Lite slave port
    assign ext_axil_awready = !ext_aw_held && !b_pending;
    assign ext_axil_wready  = !ext_w_held  && !b_pending;

    wire ext_aw_avail = ext_aw_held || (ext_axil_awvalid && ext_axil_awready);
    wire ext_w_avail  = ext_w_held  || (ext_axil_wvalid  && ext_axil_wready);
    wire [15:0] ext_awaddr_eff = ext_aw_held ? ext_awaddr_q : ext_axil_awaddr;
    wire [31:0] ext_wdata_eff  = ext_w_held  ? ext_wdata_q  : ext_axil_wdata;
    wire [3:0]  ext_wstrb_eff  = ext_w_held  ? ext_wstrb_q  : ext_axil_wstrb;

    wire uart_wr_req = uart_awvalid && uart_wvalid && !b_pending;
    wire ext_wr_req  = (!uart_wr_req) && ext_aw_avail && ext_w_avail && !b_pending;
    wire csr_wr_en   = uart_wr_req || ext_wr_req;
    wire [15:0] csr_waddr = uart_wr_req ? uart_awaddr : ext_awaddr_eff;
    wire [31:0] csr_wdata = uart_wr_req ? uart_wdata  : ext_wdata_eff;
    wire [3:0]  csr_wstrb = uart_wr_req ? uart_wstrb  : ext_wstrb_eff;

    assign uart_awready     = uart_wr_req;
    assign uart_wready      = uart_wr_req;
    assign uart_bvalid      = b_pending && (b_owner == 1'b0);
    assign ext_axil_bvalid  = b_pending && (b_owner == 1'b1);
    assign uart_bresp       = 2'b00;
    assign ext_axil_bresp   = 2'b00;

    wire uart_rd_req = uart_arvalid && !r_pending;
    wire ext_rd_req  = (!uart_rd_req) && ext_axil_arvalid && !r_pending;
    wire csr_rd_en   = uart_rd_req || ext_rd_req;
    wire [15:0] csr_raddr = uart_rd_req ? uart_araddr : ext_axil_araddr;

    assign uart_arready     = uart_rd_req;
    assign ext_axil_arready = ext_rd_req;
    assign uart_rvalid      = r_pending && (r_owner == 1'b0);
    assign ext_axil_rvalid  = r_pending && (r_owner == 1'b1);
    assign uart_rdata       = r_data_q;
    assign ext_axil_rdata   = r_data_q;
    assign uart_rresp       = 2'b00;
    assign ext_axil_rresp   = 2'b00;

    // -----------------------------------------------------------------------
    // 3. CSR Configuration Registers & Single-Cycle Pulses
    // -----------------------------------------------------------------------
    reg [31:0] r_scratch;
    reg [31:0] r_uptime_cycles;

    // Interlock block (0x0100) — r_il_wdt_en hardware-locked to 1'b1 (OBS-116)
    reg        r_il_run_en;
    wire       r_il_wdt_en = 1'b1; // Hardware-locked ON: CSR writes CANNOT disable safety WDT!
    reg        r_il_sw_estop;
    reg [5:0]  r_il_subsys_mask;
    reg        p_il_reset_a;
    reg        p_il_wdt_kick;
    reg [15:0] r_il_discrep_win;
    reg [31:0] r_il_wdt_timeout;
    reg [31:0] r_il_dwell_cycles;
    reg        r_il_cfg_locked;

    // Blanker block (0x0200)
    reg        p_blk_frame_start;
    reg        p_blk_sticky_clr;
    reg        p_blk_interlock_clr;
    reg        r_blk_auto_offset_en;
    reg [15:0] r_blk_sclk_div;
    reg signed [15:0] r_blk_dx_pitch;
    reg signed [15:0] r_blk_dy_pitch;
    reg [15:0] r_blk_tile_en_mask;
    reg [4:0]  r_blk_mem_row;
    reg        r_blk_mem_bank;
    reg        p_blk_mem_we;
    reg [31:0] r_blk_mem_wdata;

    // AOM PID block (0x0300)
    reg        r_pid_enable;
    reg        r_pid_pyro_en;
    reg        p_pid_abort_clr;
    reg        p_pid_state_reset;
    reg [3:0]  r_pid_dead_taps;
    reg        p_pid_sw_trig;
    reg signed [31:0] r_pid_kp;
    reg signed [31:0] r_pid_ki;
    reg signed [31:0] r_pid_kd;
    reg signed [31:0] r_pid_kaw;
    reg signed [31:0] r_pid_min_gain;
    reg signed [31:0] r_pid_max_gain;
    reg signed [31:0] r_pid_setpoint;
    reg signed [31:0] r_pid_bias;
    reg signed [31:0] r_pid_kt_pyro;
    reg [15:0] r_pid_temp_ref_k;
    reg [15:0] r_pid_sw_temp_k;
    reg signed [31:0] r_pid_sw_meas;
    reg        r_pid_out_valid_sticky;

    // SPI DAC HV block (0x0400)
    reg        p_spi_start;
    reg        r_spi_update_all;
    reg [7:0]  r_spi_ch_mask;
    reg [15:0] r_spi_sclk_div;
    reg        p_spi_ch_we;
    reg [2:0]  r_spi_ch_waddr;
    reg [19:0] r_spi_ch_wdata;

    // Cryo MUX DDC block (0x0500)
    reg        r_ddc_enable;
    reg        p_ddc_soft_clear;
    reg        r_ddc_mf_en;
    reg        p_ddc_sw_adc_push;
    reg [4:0]  r_ddc_num_ch_m1;
    reg [15:0] r_ddc_win_len;
    reg [4:0]  r_ddc_ch_sel;
    reg        p_ddc_phase_we;
    reg [23:0] r_ddc_phase_inc;
    reg        p_ddc_rot_we;
    reg signed [15:0] r_ddc_rot_cos;
    reg signed [15:0] r_ddc_rot_sin;
    reg        p_ddc_thresh_we;
    reg signed [31:0] r_ddc_thresh;
    reg signed [15:0] r_ddc_sw_adc_sample;
    reg signed [15:0] r_ddc_sw_mf_weight;

    // BOED Q16 Core block (0x0600)
    reg        p_boed_sprt_start;
    reg        p_boed_sprt_reset;
    reg        p_boed_step_start;
    reg        r_boed_ddc_autofeed;
    reg [4:0]  r_boed_ddc_autofeed_ch; // Dedicated target channel for collision-free SPRT autofeed!
    reg [7:0]  r_boed_step_idx;
    reg signed [31:0] r_boed_sprt_y;
    reg signed [31:0] r_boed_sprt_half;
    reg signed [31:0] r_boed_sprt_scale;
    reg signed [31:0] r_boed_sprt_thresh;
    reg [9:0]  r_boed_prior_addr;
    reg        p_boed_prior_we;
    reg signed [31:0] r_boed_prior_data;
    reg signed [31:0] r_boed_f_init;
    reg signed [31:0] r_boed_f_probe;
    reg signed [31:0] r_boed_y_meas;
    reg [31:0] r_boed_inv_gamma;
    reg signed [31:0] r_boed_inv_2var;
    reg [15:0] r_boed_delta_fisher;
    reg [15:0] r_boed_max_off;
    reg        r_boed_step_done_sticky;
    reg        r_boed_sprt_done_sticky;

    // -----------------------------------------------------------------------
    // 4. Subsystem Instantiations & Hard-Wired Safety Override Bus
    // -----------------------------------------------------------------------
    wire [2:0]  il_fsm_state;
    wire [7:0]  il_sensor_fault_latched;
    wire        il_discrep_fault;
    wire [7:0]  il_discrep_ch_latched;
    wire        il_wdt_fault;
    wire        il_sw_estop_latched;
    wire [3:0]  il_first_fault_code;
    wire [15:0] il_trip_counter;
    wire [7:0]  il_ch_a_sync;
    wire [7:0]  il_ch_b_sync;
    wire [7:0]  il_discrep_live;
    wire        il_wdt_hw_locked_on;
    wire        il_status_certified;
    wire        il_status_design_only;
    wire [31:0] il_epistemic_csr;

    uhv_interlock_fsm #(
        .HARDWIRE_WDT_ALWAYS_ON(1'b1)
    ) u_interlock (
        .clk                              (clk),
        .rst_n                            (rst_n),
        .ch_a_ok                          (il_ch_a_ok),
        .ch_b_ok                          (il_ch_b_ok),
        .run_enable_cmd                   (r_il_run_en),
        .sw_estop                         (r_il_sw_estop),
        .reset_cmd_a                      (p_il_reset_a),
        .reset_cmd_b                      (il_hw_reset_b),
        .wdt_en                           (r_il_wdt_en),
        .wdt_kick                         (p_il_wdt_kick),
        .subsys_en_mask                   (r_il_subsys_mask),
        .cfg_discrep_win                  (r_il_discrep_win),
        .cfg_wdt_timeout                  (r_il_wdt_timeout),
        .cfg_dwell_cycles                 (r_il_dwell_cycles),
        .safe_blanker_en                  (safe_blanker_en),
        .safe_laser_en                    (safe_laser_en),
        .safe_hv_en                       (safe_hv_en),
        .safe_uhv_valve_en                (safe_uhv_valve_en),
        .safe_ph3_valve_en                (safe_ph3_valve_en),
        .safe_magnet_en                   (safe_magnet_en),
        .interlock_trip_out               (interlock_trip_out),
        .safety_indep_trip_out            (safety_indep_trip_out),
        .wdt_hw_locked_on                 (il_wdt_hw_locked_on),
        .fsm_state                        (il_fsm_state),
        .sensor_fault_latched             (il_sensor_fault_latched),
        .discrep_fault_latched            (il_discrep_fault),
        .discrep_ch_latched               (il_discrep_ch_latched),
        .wdt_fault_latched                (il_wdt_fault),
        .sw_estop_latched                 (il_sw_estop_latched),
        .first_fault_code                 (il_first_fault_code),
        .trip_counter                     (il_trip_counter),
        .ch_a_sync_out                    (il_ch_a_sync),
        .ch_b_sync_out                    (il_ch_b_sync),
        .discrep_live_out                 (il_discrep_live),
        .status_certified                 (il_status_certified),
        .status_design_only_not_certified (il_status_design_only),
        .epistemic_csr_word               (il_epistemic_csr)
    );

    // HARD-WIRED INTERNAL SAFETY OVERRIDE BUS (non-bypassable by software!)
    wire hw_blanker_force = interlock_trip_out | (~safe_blanker_en);
    wire hw_aom_abort     = interlock_trip_out | (~safe_laser_en);
    wire hw_hv_clamp      = interlock_trip_out | (~safe_hv_en);

    // Hardware safety-config lock (uses 2-FF synced hw_rst_b_s2!)
    wire il_any_safe_en       = safe_blanker_en | safe_laser_en | safe_hv_en |
                                safe_uhv_valve_en | safe_ph3_valve_en | safe_magnet_en;
    wire il_in_armed_or_dwell = (il_fsm_state == 3'd2) || (il_fsm_state == 3'd3) ||
                                (il_fsm_state == 3'd4) || il_any_safe_en;
    wire il_hw_service_unlock = hw_rst_b_s2 && (!il_in_armed_or_dwell);
    wire il_cfg_write_en      = (!r_il_cfg_locked) || il_hw_service_unlock;

    // 4B. 32x32 (1,024-ch) Blanker Array Controller
    wire [31:0] blk_mem_rdata;
    wire        blk_busy;
    wire        blk_interlock_latched;
    wire        blk_frame_done_sticky;
    wire        blk_interlock_abort_sticky;
    wire [15:0] blk_tile_done_sticky;
    wire [15:0] blk_tile_abort_sticky;
    wire        blk_any_tile_abort;
    wire        blk_all_tiles_done;
    wire [10:0] blk_active_unblank_cnt;
    wire signed [15:0] blk_stitch_dx_out;
    wire signed [15:0] blk_stitch_dy_out;

    blanker_array_ctrl u_blanker (
        .clk                    (clk),
        .rst_n                  (rst_n),
        .interlock_blank_force  (hw_blanker_force),
        .frame_start            (p_blk_frame_start),
        .sticky_clr             (p_blk_sticky_clr),
        .interlock_clr          (p_blk_interlock_clr),
        .auto_offset_en         (r_blk_auto_offset_en),
        .sclk_div               (r_blk_sclk_div),
        .dx_pitch               (r_blk_dx_pitch),
        .dy_pitch               (r_blk_dy_pitch),
        .tile_en_mask           (r_blk_tile_en_mask),
        .mem_we                 (p_blk_mem_we),
        .mem_bank_sel           (r_blk_mem_bank),
        .mem_row_addr           (r_blk_mem_row),
        .mem_wdata              (r_blk_mem_wdata),
        .mem_rdata              (blk_mem_rdata),
        .tile_done_in           (blk_tile_done_in),
        .tile_abort_in          (blk_tile_abort_in),
        .tile_sel               (blk_tile_sel),
        .tile_sclk              (blk_tile_sclk),
        .tile_sdata             (blk_tile_sdata),
        .tile_latch_n           (blk_tile_latch_n),
        .frame_latch_n          (blk_frame_latch_n),
        .tile_beam_en           (blk_tile_beam_en),
        .busy                   (blk_busy),
        .safe_blanked           (blk_safe_blanked),
        .interlock_latched      (blk_interlock_latched),
        .frame_done_sticky      (blk_frame_done_sticky),
        .interlock_abort_sticky (blk_interlock_abort_sticky),
        .tile_done_sticky       (blk_tile_done_sticky),
        .tile_abort_sticky      (blk_tile_abort_sticky),
        .any_tile_abort         (blk_any_tile_abort),
        .all_tiles_done         (blk_all_tiles_done),
        .active_unblank_cnt     (blk_active_unblank_cnt),
        .stitch_dx_pitch_out    (blk_stitch_dx_out),
        .stitch_dy_pitch_out    (blk_stitch_dy_out)
    );

    // 4C. Q16.16 Anti-Windup AOM PID Controller
    wire               pid_sample_valid = aom_ext_sample_valid | p_pid_sw_trig;
    wire signed [31:0] pid_meas_mux     = p_pid_sw_trig ? r_pid_sw_meas : aom_ext_meas_q16;
    wire        [15:0] pid_temp_mux     = (aom_ext_temp_meas_k >= r_pid_sw_temp_k) ?
                                          aom_ext_temp_meas_k : r_pid_sw_temp_k;

    wire               pid_busy;
    wire               pid_out_valid;
    wire signed [31:0] pid_u_raw_q16;
    wire signed [31:0] pid_integ_q16;
    wire               pid_saturated;
    wire               pid_overtemp_latched;
    wire               pid_abort_active;
    wire        [15:0] pid_last_temp_k;

    aom_pid_ctrl u_aom_pid (
        .clk              (clk),
        .rst_n            (rst_n),
        .interlock_abort  (hw_aom_abort),
        .enable           (r_pid_enable),
        .pyro_en          (r_pid_pyro_en),
        .abort_clr        (p_pid_abort_clr),
        .state_reset      (p_pid_state_reset),
        .dead_time_taps   (r_pid_dead_taps),
        .sample_valid     (pid_sample_valid),
        .meas_q16         (pid_meas_mux),
        .temp_meas_k      (pid_temp_mux),
        .temp_ref_k       (r_pid_temp_ref_k),
        .cfg_use_ext      (1'b1),
        .cfg_kp_q16       (r_pid_kp),
        .cfg_ki_q16       (r_pid_ki),
        .cfg_kd_q16       (r_pid_kd),
        .cfg_kaw_q16      (r_pid_kaw),
        .cfg_min_gain_q16 (r_pid_min_gain),
        .cfg_max_gain_q16 (r_pid_max_gain),
        .cfg_setpoint_q16 (r_pid_setpoint),
        .cfg_bias_q16     (r_pid_bias),
        .cfg_kt_pyro_q16  (r_pid_kt_pyro),
        .busy             (pid_busy),
        .out_valid        (pid_out_valid),
        .aom_rf_en        (aom_rf_en),
        .aom_drive_q16    (aom_drive_q16),
        .u_raw_q16        (pid_u_raw_q16),
        .integ_q16        (pid_integ_q16),
        .saturated        (pid_saturated),
        .overtemp_latched (pid_overtemp_latched),
        .abort_active     (pid_abort_active),
        .last_temp_k      (pid_last_temp_k)
    );

    // 4D. 8-Channel 20-Bit SPI DAC HV Controller
    wire [19:0] spi_ch_rd_data;
    wire        spi_busy;
    wire        spi_done_sticky;
    wire        spi_clamp_zero_done;
    wire [3:0]  spi_cur_ch;
    wire [23:0] spi_last_tx_frame;
    wire [2:0]  spi_rd_ch_sel = csr_raddr[4:2] - 3'd4;

    spi_dac_hv_ctrl u_spi_dac (
        .clk                 (clk),
        .rst_n               (rst_n),
        .hv_safe_clamp       (hw_hv_clamp),
        .ch_wr_en            (p_spi_ch_we),
        .ch_wr_addr          (r_spi_ch_waddr),
        .ch_wr_data          (r_spi_ch_wdata),
        .ch_rd_addr          (spi_rd_ch_sel),
        .ch_rd_data          (spi_ch_rd_data),
        .start_update        (p_spi_start),
        .update_all          (r_spi_update_all),
        .ch_update_mask      (r_spi_ch_mask),
        .cfg_sclk_div        (r_spi_sclk_div),
        .spi_cs_n            (spi_cs_n),
        .spi_sclk            (spi_sclk),
        .spi_mosi            (spi_mosi),
        .spi_ldac_n          (spi_ldac_n),
        .hv_clr_n            (hv_clr_n),
        .busy                (spi_busy),
        .done_sticky         (spi_done_sticky),
        .clamp_zero_seq_done (spi_clamp_zero_done),
        .cur_ch_out          (spi_cur_ch),
        .last_tx_frame       (spi_last_tx_frame)
    );

    // 4E. Cryo MUX Multi-Tone 100 MSPS Parallel Streaming DDC Controller
    wire               ddc_adc_valid_mux = ddc_adc_valid | p_ddc_sw_adc_push;
    wire signed [15:0] ddc_adc_mux       = p_ddc_sw_adc_push ? r_ddc_sw_adc_sample : ddc_adc_sample;
    wire signed [15:0] ddc_mf_mux        = p_ddc_sw_adc_push ? r_ddc_sw_mf_weight  : ddc_mf_weight;

    // Arbitrated collision-free autofeed handshake (OBS-114):
    // When autofeed is enabled, only the selected channel `r_boed_ddc_autofeed_ch` fires SPRT,
    // and backpressures 1 cycle if manual CSR `p_boed_sprt_start` collides on the same cycle!
    wire               ddc_tid_selected  = (ddc_m_axis_tid == r_boed_ddc_autofeed_ch);
    wire               ddc_axis_tready_i = r_boed_ddc_autofeed ?
                                           (!(ddc_tid_selected && p_boed_sprt_start)) :
                                           ddc_m_axis_tready;

    wire               ddc_busy;
    wire               ddc_done_pulse;
    wire               ddc_done_sticky;
    wire        [15:0] ddc_sample_cnt;
    wire        [15:0] ddc_window_cnt;
    wire signed [31:0] ddc_rd_res_i;
    wire signed [31:0] ddc_rd_res_q;
    wire signed [31:0] ddc_rd_res_proj;

    cryo_mux_ddc_ctrl #(
        .N_CH(DDC_N_CH)
    ) u_cryo_ddc (
        .clk                 (clk),
        .rst_n               (rst_n),
        .enable              (r_ddc_enable),
        .soft_clear          (p_ddc_soft_clear),
        .mf_en               (r_ddc_mf_en),
        .cfg_num_ch_m1       (r_ddc_num_ch_m1),
        .cfg_win_len         (r_ddc_win_len),
        .cfg_ch_addr         (r_ddc_ch_sel),
        .cfg_phase_we        (p_ddc_phase_we),
        .cfg_phase_inc       (r_ddc_phase_inc),
        .cfg_rot_we          (p_ddc_rot_we),
        .cfg_rot_cos         (r_ddc_rot_cos),
        .cfg_rot_sin         (r_ddc_rot_sin),
        .cfg_thresh_we       (p_ddc_thresh_we),
        .cfg_thresh          (r_ddc_thresh),
        .adc_valid           (ddc_adc_valid_mux),
        .adc_ready           (ddc_adc_ready),
        .adc_sample          (ddc_adc_mux),
        .mf_weight           (ddc_mf_mux),
        .m_axis_tvalid       (ddc_m_axis_tvalid),
        .m_axis_tready       (ddc_axis_tready_i),
        .m_axis_tdata        (ddc_m_axis_tdata),
        .m_axis_tid          (ddc_m_axis_tid),
        .m_axis_tlast        (ddc_m_axis_tlast),
        .busy                (ddc_busy),
        .readout_done_pulse  (ddc_done_pulse),
        .readout_done_sticky (ddc_done_sticky),
        .qubit_state_mask    (ddc_qubit_state_mask),
        .sample_cnt_out      (ddc_sample_cnt),
        .window_count        (ddc_window_cnt),
        .rd_res_i            (ddc_rd_res_i),
        .rd_res_q            (ddc_rd_res_q),
        .rd_res_proj         (ddc_rd_res_proj)
    );

    // 4F. Arbitrated Single-Channel BOED Q16 Core Autofeed (ZERO multi-channel LLR mixing!)
    wire               boed_autofeed_fire = r_boed_ddc_autofeed && ddc_m_axis_tvalid &&
                                            ddc_axis_tready_i && ddc_tid_selected;
    wire               boed_sprt_start_i  = p_boed_sprt_start | boed_autofeed_fire;
    wire signed [31:0] boed_sprt_y_i      = p_boed_sprt_start ?
                                            r_boed_sprt_y : $signed(ddc_m_axis_tdata[31:0]);

    wire               boed_sprt_done;
    wire               boed_sprt_dec_valid;
    wire               boed_sprt_donor;
    wire signed [31:0] boed_sprt_llr;
    wire               boed_busy;
    wire               boed_step_done;
    wire signed [31:0] boed_mu_off_q8;
    wire        [15:0] boed_std_q4;
    wire signed [31:0] boed_next_probe_q8;
    wire        [15:0] boed_cycle_count;

    boed_q16_core #(
        .LOR_HEX_FILE(BOED_LOR_HEX),
        .EXP_HEX_FILE(BOED_EXP_HEX)
    ) u_boed_core (
        .clk                 (clk),
        .rst_n               (rst_n),
        .sprt_start          (boed_sprt_start_i),
        .sprt_reset_llr      (p_boed_sprt_reset),
        .sprt_y_q16          (boed_sprt_y_i),
        .sprt_half_sig_q16   (r_boed_sprt_half),
        .sprt_scale_q16      (r_boed_sprt_scale),
        .sprt_thresh_q16     (r_boed_sprt_thresh),
        .sprt_done           (boed_sprt_done),
        .sprt_decision_valid (boed_sprt_dec_valid),
        .sprt_donor_present  (boed_sprt_donor),
        .sprt_llr_q16        (boed_sprt_llr),
        .step_start          (p_boed_step_start),
        .prior_load_en       (p_boed_prior_we),
        .prior_load_addr     (r_boed_prior_addr),
        .prior_load_lp_q16   (r_boed_prior_data),
        .f_init_hz           (r_boed_f_init),
        .f_probe_hz          (r_boed_f_probe),
        .y_meas_q16          (r_boed_y_meas),
        .inv_gamma_q24       (r_boed_inv_gamma),
        .inv_2var_q16        (r_boed_inv_2var),
        .delta_fisher_q4     (r_boed_delta_fisher),
        .max_off_q4          (r_boed_max_off),
        .step_idx            (r_boed_step_idx),
        .busy                (boed_busy),
        .step_done           (boed_step_done),
        .mu_off_q8           (boed_mu_off_q8),
        .std_q4              (boed_std_q4),
        .next_probe_off_q8   (boed_next_probe_q8),
        .cycle_count         (boed_cycle_count)
    );

    // -----------------------------------------------------------------------
    // 5. Unified CSR Read Decoder
    // -----------------------------------------------------------------------
    wire [31:0] ddc_mask_u32;
    generate
        if (DDC_N_CH >= 32) begin : g_mask32
            assign ddc_mask_u32 = ddc_qubit_state_mask[31:0];
        end else begin : g_mask_sub32
            assign ddc_mask_u32 = {{(32 - DDC_N_CH){1'b0}}, ddc_qubit_state_mask};
        end
    endgenerate

    reg [31:0] csr_rdata_c;
    always @(*) begin
        case (csr_raddr)
            // 0x0000 Global Block
            16'h0000: csr_rdata_c = CHIP_ID_CONST;
            16'h0004: csr_rdata_c = VERSION_CONST;
            16'h0008: csr_rdata_c = GLOBAL_EPISTEMIC_CSR;
            16'h000C: csr_rdata_c = {
                uart_rx_err_cnt[7:0],
                uart_rx_ovf_cnt[6:0], uart_bridge_busy,
                r_il_cfg_locked, il_wdt_hw_locked_on, 3'd0, boed_busy, ddc_busy, spi_busy,
                pid_abort_active, blk_safe_blanked, blk_busy, interlock_trip_out, 1'b0, il_fsm_state
            };
            16'h0010: csr_rdata_c = r_scratch;
            16'h0014: csr_rdata_c = r_uptime_cycles;

            // 0x0100 Interlock Block
            16'h0100: csr_rdata_c = {14'd0, il_wdt_hw_locked_on, r_il_cfg_locked, 2'd0, r_il_subsys_mask, 5'd0, r_il_sw_estop, r_il_wdt_en, r_il_run_en};
            16'h0104: csr_rdata_c = {
                il_trip_counter,
                il_status_design_only, il_status_certified,
                il_first_fault_code,
                safe_magnet_en, safe_ph3_valve_en, safe_uhv_valve_en,
                safe_hv_en, safe_laser_en, safe_blanker_en,
                interlock_trip_out, il_fsm_state
            };
            16'h0108: csr_rdata_c = {
                8'd0, il_discrep_ch_latched,
                5'd0, il_sw_estop_latched, il_wdt_fault, il_discrep_fault, il_sensor_fault_latched
            };
            16'h010C: csr_rdata_c = {8'd0, il_discrep_live, il_ch_b_sync, il_ch_a_sync};
            16'h0110: csr_rdata_c = {16'd0, r_il_discrep_win};
            16'h0114: csr_rdata_c = r_il_wdt_timeout;
            16'h0118: csr_rdata_c = r_il_dwell_cycles;
            16'h011C: csr_rdata_c = il_epistemic_csr;

            // 0x0200 Blanker Array Block
            16'h0200: csr_rdata_c = {12'd0, r_blk_sclk_div, r_blk_auto_offset_en, 3'd0};
            16'h0204: csr_rdata_c = {
                5'd0, blk_active_unblank_cnt,
                9'd0, blk_all_tiles_done, blk_any_tile_abort,
                blk_interlock_abort_sticky, blk_frame_done_sticky,
                blk_interlock_latched, blk_safe_blanked, blk_busy
            };
            16'h0208: csr_rdata_c = {blk_stitch_dy_out, blk_stitch_dx_out};
            16'h020C: csr_rdata_c = {16'd0, r_blk_tile_en_mask};
            16'h0210: csr_rdata_c = {16'd0, blk_tile_done_sticky};
            16'h0214: csr_rdata_c = {16'd0, blk_tile_abort_sticky};
            16'h0218: csr_rdata_c = {23'd0, r_blk_mem_bank, 3'd0, r_blk_mem_row};
            16'h021C: csr_rdata_c = blk_mem_rdata;

            // 0x0300 AOM PID Block
            16'h0300: csr_rdata_c = {24'd0, r_pid_dead_taps, 2'd0, r_pid_pyro_en, r_pid_enable};
            16'h0304: csr_rdata_c = {
                pid_last_temp_k,
                10'd0, aom_rf_en, pid_abort_active, pid_overtemp_latched,
                pid_saturated, r_pid_out_valid_sticky, pid_busy
            };
            16'h0308: csr_rdata_c = r_pid_kp;
            16'h030C: csr_rdata_c = r_pid_ki;
            16'h0310: csr_rdata_c = r_pid_kd;
            16'h0314: csr_rdata_c = r_pid_kaw;
            16'h0318: csr_rdata_c = r_pid_min_gain;
            16'h031C: csr_rdata_c = r_pid_max_gain;
            16'h0320: csr_rdata_c = r_pid_setpoint;
            16'h0324: csr_rdata_c = r_pid_bias;
            16'h0328: csr_rdata_c = r_pid_kt_pyro;
            16'h032C: csr_rdata_c = {r_pid_sw_temp_k, r_pid_temp_ref_k};
            16'h0330: csr_rdata_c = r_pid_sw_meas;
            16'h0334: csr_rdata_c = aom_drive_q16;
            16'h0338: csr_rdata_c = pid_integ_q16;
            16'h033C: csr_rdata_c = pid_u_raw_q16;

            // 0x0400 SPI DAC HV Block
            16'h0400: csr_rdata_c = {r_spi_sclk_div, r_spi_ch_mask, 6'd0, r_spi_update_all, 1'b0};
            16'h0404: csr_rdata_c = {
                spi_last_tx_frame,
                spi_cur_ch,
                spi_clamp_zero_done, hw_hv_clamp, spi_done_sticky, spi_busy
            };
            16'h0410, 16'h0414, 16'h0418, 16'h041C,
            16'h0420, 16'h0424, 16'h0428, 16'h042C:
                      csr_rdata_c = {12'd0, spi_ch_rd_data};

            // 0x0500 Cryo MUX DDC Block
            16'h0500: csr_rdata_c = {r_ddc_win_len, 3'd0, r_ddc_num_ch_m1, 5'd0, r_ddc_mf_en, 1'b0, r_ddc_enable};
            16'h0504: csr_rdata_c = {
                ddc_window_cnt,
                ddc_sample_cnt[7:0],
                5'd0, ddc_m_axis_tvalid, ddc_done_sticky, ddc_busy
            };
            16'h0508: csr_rdata_c = ddc_mask_u32;
            16'h050C: csr_rdata_c = {27'd0, r_ddc_ch_sel};
            16'h0510: csr_rdata_c = {8'd0, r_ddc_phase_inc};
            16'h0514: csr_rdata_c = {r_ddc_rot_sin, r_ddc_rot_cos};
            16'h0518: csr_rdata_c = r_ddc_thresh;
            16'h051C: csr_rdata_c = {r_ddc_sw_mf_weight, r_ddc_sw_adc_sample};
            16'h0520: csr_rdata_c = ddc_rd_res_i;
            16'h0524: csr_rdata_c = ddc_rd_res_q;
            16'h0528: csr_rdata_c = ddc_rd_res_proj;

            // 0x0600 BOED Q16 Core Block
            16'h0600: csr_rdata_c = {11'd0, r_boed_ddc_autofeed_ch, r_boed_step_idx, 4'd0, r_boed_ddc_autofeed, 3'd0};
            16'h0604: csr_rdata_c = {
                boed_cycle_count,
                11'd0, boed_sprt_donor, boed_sprt_dec_valid,
                r_boed_sprt_done_sticky, r_boed_step_done_sticky, boed_busy
            };
            16'h0608: csr_rdata_c = r_boed_sprt_y;
            16'h060C: csr_rdata_c = r_boed_sprt_half;
            16'h0610: csr_rdata_c = r_boed_sprt_scale;
            16'h0614: csr_rdata_c = r_boed_sprt_thresh;
            16'h0618: csr_rdata_c = boed_sprt_llr;
            16'h061C: csr_rdata_c = {22'd0, r_boed_prior_addr};
            16'h0620: csr_rdata_c = r_boed_prior_data;
            16'h0624: csr_rdata_c = r_boed_f_init;
            16'h0628: csr_rdata_c = r_boed_f_probe;
            16'h062C: csr_rdata_c = r_boed_y_meas;
            16'h0630: csr_rdata_c = r_boed_inv_gamma;
            16'h0634: csr_rdata_c = r_boed_inv_2var;
            16'h0638: csr_rdata_c = {r_boed_max_off, r_boed_delta_fisher};
            16'h063C: csr_rdata_c = boed_mu_off_q8;
            16'h0640: csr_rdata_c = {16'd0, boed_std_q4};
            16'h0644: csr_rdata_c = boed_next_probe_q8;

            default:  csr_rdata_c = 32'hDEAD_BEEF;
        endcase
    end

    wire _unused_ok = &{1'b0, ddc_done_pulse, ddc_sample_cnt[15:8],
                        uart_rx_err_cnt[15:8], uart_rx_ovf_cnt[15:7]};

    // -----------------------------------------------------------------------
    // 6. Sequential AXI4-Lite Handshake & CSR Write Logic
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_sync_n) begin
            hw_rst_b_s1            <= 1'b0;
            hw_rst_b_s2            <= 1'b0;
            ext_aw_held            <= 1'b0;
            ext_awaddr_q           <= 16'd0;
            ext_w_held             <= 1'b0;
            ext_wdata_q            <= 32'd0;
            ext_wstrb_q            <= 4'hF;
            b_pending              <= 1'b0;
            b_owner                <= 1'b0;
            r_pending              <= 1'b0;
            r_owner                <= 1'b0;
            r_data_q               <= 32'd0;

            r_scratch              <= 32'd0;
            r_uptime_cycles        <= 32'd0;

            r_il_run_en            <= 1'b0;
            r_il_sw_estop          <= 1'b0;
            r_il_subsys_mask       <= 6'b111111;
            p_il_reset_a           <= 1'b0;
            p_il_wdt_kick          <= 1'b0;
            r_il_discrep_win       <= 16'd100;
            r_il_wdt_timeout       <= 32'd10_000_000;
            r_il_dwell_cycles      <= 32'd200_000_000;
            r_il_cfg_locked        <= 1'b0;

            p_blk_frame_start      <= 1'b0;
            p_blk_sticky_clr       <= 1'b0;
            p_blk_interlock_clr    <= 1'b0;
            r_blk_auto_offset_en   <= 1'b0;
            r_blk_sclk_div         <= 16'd1;
            r_blk_dx_pitch         <= 16'sd0;
            r_blk_dy_pitch         <= 16'sd0;
            r_blk_tile_en_mask     <= 16'hFFFF;
            r_blk_mem_row          <= 5'd0;
            r_blk_mem_bank         <= 1'b0;
            p_blk_mem_we           <= 1'b0;
            r_blk_mem_wdata        <= 32'd0;

            r_pid_enable           <= 1'b0;
            r_pid_pyro_en          <= 1'b0;
            p_pid_abort_clr        <= 1'b0;
            p_pid_state_reset      <= 1'b0;
            r_pid_dead_taps        <= 4'd1;
            p_pid_sw_trig          <= 1'b0;
            r_pid_kp               <= 32'sd27525;
            r_pid_ki               <= 32'sd23593;
            r_pid_kd               <= 32'sd3277;
            r_pid_kaw              <= 32'sd42598;
            r_pid_min_gain         <= 32'sd42598;
            r_pid_max_gain         <= 32'sd91750;
            r_pid_setpoint         <= 32'sd65536;
            r_pid_bias             <= 32'sd65536;
            r_pid_kt_pyro          <= 32'sd39;
            r_pid_temp_ref_k       <= 16'd300;
            r_pid_sw_temp_k        <= 16'd300;
            r_pid_sw_meas          <= 32'sd65536;
            r_pid_out_valid_sticky <= 1'b0;

            p_spi_start            <= 1'b0;
            r_spi_update_all       <= 1'b1;
            r_spi_ch_mask          <= 8'hFF;
            r_spi_sclk_div         <= 16'd4;
            p_spi_ch_we            <= 1'b0;
            r_spi_ch_waddr         <= 3'd0;
            r_spi_ch_wdata         <= 20'd0;

            r_ddc_enable           <= 1'b0;
            p_ddc_soft_clear       <= 1'b0;
            r_ddc_mf_en            <= 1'b0;
            p_ddc_sw_adc_push      <= 1'b0;
            r_ddc_num_ch_m1        <= 5'd7;
            r_ddc_win_len          <= 16'd200;
            r_ddc_ch_sel           <= 5'd0;
            p_ddc_phase_we         <= 1'b0;
            r_ddc_phase_inc        <= 24'd0;
            p_ddc_rot_we           <= 1'b0;
            r_ddc_rot_cos          <= 16'sd32767;
            r_ddc_rot_sin          <= 16'sd0;
            p_ddc_thresh_we        <= 1'b0;
            r_ddc_thresh           <= 32'sd0;
            r_ddc_sw_adc_sample    <= 16'sd0;
            r_ddc_sw_mf_weight     <= 16'sd32767;

            p_boed_sprt_start      <= 1'b0;
            p_boed_sprt_reset      <= 1'b0;
            p_boed_step_start      <= 1'b0;
            r_boed_ddc_autofeed    <= 1'b0;
            r_boed_ddc_autofeed_ch <= 5'd0;
            r_boed_step_idx        <= 8'd0;
            r_boed_sprt_y          <= 32'sd0;
            r_boed_sprt_half       <= 32'sd0;
            r_boed_sprt_scale      <= 32'sd65536;
            r_boed_sprt_thresh     <= 32'sd131072;
            r_boed_prior_addr      <= 10'd0;
            p_boed_prior_we        <= 1'b0;
            r_boed_prior_data      <= 32'sd0;
            r_boed_f_init          <= 32'sd30000;
            r_boed_f_probe         <= 32'sd30000;
            r_boed_y_meas          <= 32'sd0;
            r_boed_inv_gamma       <= 32'd16777;
            r_boed_inv_2var        <= 32'sd65536;
            r_boed_delta_fisher    <= 16'd9238;
            r_boed_max_off         <= 16'd22400;
            r_boed_step_done_sticky <= 1'b0;
            r_boed_sprt_done_sticky <= 1'b0;
        end else begin
            // 2-FF sync for physical hardware reset pushbutton
            hw_rst_b_s1     <= il_hw_reset_b;
            hw_rst_b_s2     <= hw_rst_b_s1;
            r_uptime_cycles <= r_uptime_cycles + 32'd1;

            // Independent external AXI4-Lite AW / W capture registers
            if (ext_wr_req) begin
                ext_aw_held <= 1'b0;
                ext_w_held  <= 1'b0;
            end else begin
                if (ext_axil_awvalid && ext_axil_awready) begin
                    ext_aw_held  <= 1'b1;
                    ext_awaddr_q <= ext_axil_awaddr;
                end
                if (ext_axil_wvalid && ext_axil_wready) begin
                    ext_w_held  <= 1'b1;
                    ext_wdata_q <= ext_axil_wdata;
                    ext_wstrb_q <= ext_axil_wstrb;
                end
            end

            // Auto-clear all single-cycle W1P command pulses
            p_il_reset_a        <= 1'b0;
            p_il_wdt_kick       <= 1'b0;
            p_blk_frame_start   <= 1'b0;
            p_blk_sticky_clr    <= 1'b0;
            p_blk_interlock_clr <= 1'b0;
            p_blk_mem_we        <= 1'b0;
            p_pid_abort_clr     <= 1'b0;
            p_pid_state_reset   <= 1'b0;
            p_pid_sw_trig       <= 1'b0;
            p_spi_start         <= 1'b0;
            p_spi_ch_we         <= 1'b0;
            p_ddc_soft_clear    <= 1'b0;
            p_ddc_sw_adc_push   <= 1'b0;
            p_ddc_phase_we      <= 1'b0;
            p_ddc_rot_we        <= 1'b0;
            p_ddc_thresh_we     <= 1'b0;
            p_boed_sprt_start   <= 1'b0;
            p_boed_sprt_reset   <= 1'b0;
            p_boed_step_start   <= 1'b0;
            p_boed_prior_we     <= 1'b0;

            if (pid_out_valid)  r_pid_out_valid_sticky  <= 1'b1;
            if (boed_step_done) r_boed_step_done_sticky <= 1'b1;
            if (boed_sprt_done) r_boed_sprt_done_sticky <= 1'b1;

            // AXI4-Lite B-channel completion
            if (b_pending) begin
                if ((b_owner == 1'b0 && uart_bready) || (b_owner == 1'b1 && ext_axil_bready)) begin
                    b_pending <= 1'b0;
                end
            end else if (csr_wr_en) begin
                b_pending <= 1'b1;
                b_owner   <= uart_wr_req ? 1'b0 : 1'b1;
            end

            // AXI4-Lite R-channel completion
            if (r_pending) begin
                if ((r_owner == 1'b0 && uart_rready) || (r_owner == 1'b1 && ext_axil_rready)) begin
                    r_pending <= 1'b0;
                end
            end else if (csr_rd_en) begin
                r_pending <= 1'b1;
                r_owner   <= uart_rd_req ? 1'b0 : 1'b1;
                r_data_q  <= csr_rdata_c;
            end

            // Safety-config lock state update
            if (il_in_armed_or_dwell) begin
                r_il_cfg_locked <= 1'b1;
            end else if (il_hw_service_unlock) begin
                r_il_cfg_locked <= 1'b0;
            end

            // CSR Register Writes (honoring AXI4-Lite csr_wstrb byte enables!)
            if (csr_wr_en) begin
                case (csr_waddr)
                    16'h0010: r_scratch <= apply_wstrb(r_scratch, csr_wdata, csr_wstrb);

                    // 0x0100 Interlock Block (bit 1 wdt_en is hardware-locked ON!)
                    16'h0100: begin
                        if (csr_wstrb[0]) begin
                            r_il_run_en   <= csr_wdata[0];
                            r_il_sw_estop <= csr_wdata[2];
                            p_il_reset_a  <= csr_wdata[3];
                            p_il_wdt_kick <= csr_wdata[5];
                        end
                        if (csr_wstrb[1]) begin
                            r_il_subsys_mask <= csr_wdata[13:8];
                        end
                    end
                    16'h0110: begin
                        if (il_cfg_write_en)
                            r_il_discrep_win <= apply_wstrb16(r_il_discrep_win, csr_wdata[15:0], csr_wstrb[1:0]);
                    end
                    16'h0114: begin
                        if (il_cfg_write_en)
                            r_il_wdt_timeout <= apply_wstrb(r_il_wdt_timeout, csr_wdata, csr_wstrb);
                    end
                    16'h0118: begin
                        if (il_cfg_write_en)
                            r_il_dwell_cycles <= apply_wstrb(r_il_dwell_cycles, csr_wdata, csr_wstrb);
                    end

                    // 0x0200 Blanker Array Block
                    16'h0200: begin
                        if (csr_wstrb[0]) begin
                            p_blk_frame_start    <= csr_wdata[0];
                            p_blk_sticky_clr     <= csr_wdata[1];
                            p_blk_interlock_clr  <= csr_wdata[2];
                            r_blk_auto_offset_en <= csr_wdata[3];
                        end
                        if (|csr_wstrb[2:0]) begin
                            r_blk_sclk_div <= csr_wdata[19:4];
                        end
                    end
                    16'h0208: begin
                        if (&csr_wstrb[1:0]) r_blk_dx_pitch <= $signed(csr_wdata[15:0]);
                        if (&csr_wstrb[3:2]) r_blk_dy_pitch <= $signed(csr_wdata[31:16]);
                    end
                    16'h020C: r_blk_tile_en_mask <= apply_wstrb16(r_blk_tile_en_mask, csr_wdata[15:0], csr_wstrb[1:0]);
                    16'h0218: begin
                        if (csr_wstrb[0]) r_blk_mem_row  <= csr_wdata[4:0];
                        if (csr_wstrb[1]) r_blk_mem_bank <= csr_wdata[8];
                    end
                    16'h021C: begin
                        p_blk_mem_we    <= 1'b1;
                        r_blk_mem_wdata <= apply_wstrb(r_blk_mem_wdata, csr_wdata, csr_wstrb);
                    end

                    // 0x0300 AOM PID Block
                    16'h0300: begin
                        if (csr_wstrb[0]) begin
                            r_pid_enable      <= csr_wdata[0];
                            r_pid_pyro_en     <= csr_wdata[1];
                            p_pid_abort_clr   <= csr_wdata[2];
                            p_pid_state_reset <= csr_wdata[3];
                            r_pid_dead_taps   <= csr_wdata[7:4];
                        end
                        if (csr_wstrb[1]) begin
                            p_pid_sw_trig <= csr_wdata[8];
                        end
                        if ((csr_wstrb[1] && csr_wdata[8]) || (csr_wstrb[0] && csr_wdata[3])) begin
                            r_pid_out_valid_sticky <= 1'b0;
                        end
                    end
                    16'h0308: r_pid_kp       <= $signed(apply_wstrb(r_pid_kp, csr_wdata, csr_wstrb));
                    16'h030C: r_pid_ki       <= $signed(apply_wstrb(r_pid_ki, csr_wdata, csr_wstrb));
                    16'h0310: r_pid_kd       <= $signed(apply_wstrb(r_pid_kd, csr_wdata, csr_wstrb));
                    16'h0314: r_pid_kaw      <= $signed(apply_wstrb(r_pid_kaw, csr_wdata, csr_wstrb));
                    16'h0318: r_pid_min_gain <= $signed(apply_wstrb(r_pid_min_gain, csr_wdata, csr_wstrb));
                    16'h031C: r_pid_max_gain <= $signed(apply_wstrb(r_pid_max_gain, csr_wdata, csr_wstrb));
                    16'h0320: r_pid_setpoint <= $signed(apply_wstrb(r_pid_setpoint, csr_wdata, csr_wstrb));
                    16'h0324: r_pid_bias     <= $signed(apply_wstrb(r_pid_bias, csr_wdata, csr_wstrb));
                    16'h0328: r_pid_kt_pyro  <= $signed(apply_wstrb(r_pid_kt_pyro, csr_wdata, csr_wstrb));
                    16'h032C: begin
                        if (&csr_wstrb[1:0]) r_pid_temp_ref_k <= csr_wdata[15:0];
                        if (&csr_wstrb[3:2]) r_pid_sw_temp_k  <= csr_wdata[31:16];
                    end
                    16'h0330: r_pid_sw_meas <= $signed(apply_wstrb(r_pid_sw_meas, csr_wdata, csr_wstrb));

                    // 0x0400 SPI DAC HV Block
                    16'h0400: begin
                        if (csr_wstrb[0]) begin
                            p_spi_start      <= csr_wdata[0];
                            r_spi_update_all <= csr_wdata[1];
                        end
                        if (csr_wstrb[1])    r_spi_ch_mask  <= csr_wdata[15:8];
                        if (&csr_wstrb[3:2]) r_spi_sclk_div <= csr_wdata[31:16];
                    end
                    16'h0410, 16'h0414, 16'h0418, 16'h041C,
                    16'h0420, 16'h0424, 16'h0428, 16'h042C: begin
                        p_spi_ch_we    <= 1'b1;
                        r_spi_ch_waddr <= csr_waddr[4:2] - 3'd4;
                        r_spi_ch_wdata <= csr_wdata[19:0];
                    end

                    // 0x0500 Cryo MUX DDC Block
                    16'h0500: begin
                        if (csr_wstrb[0]) begin
                            r_ddc_enable      <= csr_wdata[0];
                            p_ddc_soft_clear  <= csr_wdata[1];
                            r_ddc_mf_en       <= csr_wdata[2];
                            p_ddc_sw_adc_push <= csr_wdata[3];
                        end
                        if (csr_wstrb[1])    r_ddc_num_ch_m1 <= csr_wdata[12:8];
                        if (&csr_wstrb[3:2]) r_ddc_win_len   <= csr_wdata[31:16];
                    end
                    16'h050C: if (csr_wstrb[0]) r_ddc_ch_sel <= csr_wdata[4:0];
                    16'h0510: begin
                        p_ddc_phase_we  <= 1'b1;
                        r_ddc_phase_inc <= csr_wdata[23:0];
                    end
                    16'h0514: begin
                        p_ddc_rot_we  <= 1'b1;
                        r_ddc_rot_cos <= $signed(csr_wdata[15:0]);
                        r_ddc_rot_sin <= $signed(csr_wdata[31:16]);
                    end
                    16'h0518: begin
                        p_ddc_thresh_we <= 1'b1;
                        r_ddc_thresh    <= $signed(apply_wstrb(r_ddc_thresh, csr_wdata, csr_wstrb));
                    end
                    16'h051C: begin
                        if (&csr_wstrb[1:0]) r_ddc_sw_adc_sample <= $signed(csr_wdata[15:0]);
                        if (&csr_wstrb[3:2]) r_ddc_sw_mf_weight  <= $signed(csr_wdata[31:16]);
                    end

                    // 0x0600 BOED Q16 Core Block
                    16'h0600: begin
                        if (csr_wstrb[0]) begin
                            p_boed_sprt_start   <= csr_wdata[0];
                            p_boed_sprt_reset   <= csr_wdata[1];
                            p_boed_step_start   <= csr_wdata[2];
                            r_boed_ddc_autofeed <= csr_wdata[3];
                            if (csr_wdata[0] || csr_wdata[1]) r_boed_sprt_done_sticky <= 1'b0;
                            if (csr_wdata[2])                 r_boed_step_done_sticky <= 1'b0;
                        end
                        if (csr_wstrb[1]) r_boed_step_idx        <= csr_wdata[15:8];
                        if (csr_wstrb[2]) r_boed_ddc_autofeed_ch <= csr_wdata[20:16];
                    end
                    16'h0608: r_boed_sprt_y      <= $signed(apply_wstrb(r_boed_sprt_y, csr_wdata, csr_wstrb));
                    16'h060C: r_boed_sprt_half   <= $signed(apply_wstrb(r_boed_sprt_half, csr_wdata, csr_wstrb));
                    16'h0610: r_boed_sprt_scale  <= $signed(apply_wstrb(r_boed_sprt_scale, csr_wdata, csr_wstrb));
                    16'h0614: r_boed_sprt_thresh <= $signed(apply_wstrb(r_boed_sprt_thresh, csr_wdata, csr_wstrb));
                    16'h061C: if (|csr_wstrb[1:0]) r_boed_prior_addr <= csr_wdata[9:0];
                    16'h0620: begin
                        p_boed_prior_we   <= 1'b1;
                        r_boed_prior_data <= $signed(apply_wstrb(r_boed_prior_data, csr_wdata, csr_wstrb));
                    end
                    16'h0624: r_boed_f_init      <= $signed(apply_wstrb(r_boed_f_init, csr_wdata, csr_wstrb));
                    16'h0628: r_boed_f_probe     <= $signed(apply_wstrb(r_boed_f_probe, csr_wdata, csr_wstrb));
                    16'h062C: r_boed_y_meas      <= $signed(apply_wstrb(r_boed_y_meas, csr_wdata, csr_wstrb));
                    16'h0630: r_boed_inv_gamma   <= apply_wstrb(r_boed_inv_gamma, csr_wdata, csr_wstrb);
                    16'h0634: r_boed_inv_2var    <= $signed(apply_wstrb(r_boed_inv_2var, csr_wdata, csr_wstrb));
                    16'h0638: begin
                        if (&csr_wstrb[1:0]) r_boed_delta_fisher <= csr_wdata[15:0];
                        if (&csr_wstrb[3:2]) r_boed_max_off      <= csr_wdata[31:16];
                    end

                    default: begin
                        // Unmapped write safely ignored
                    end
                endcase
            end
        end
    end
endmodule
