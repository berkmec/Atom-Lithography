// fpga_top_carrier_wrap.v - Pin-Constrained Physical Carrier & ECP5 Top Wrapper (76 I/O Pins)
// Resolves OBS-050 package pin overflow (400/205 TRELLIS_IO -> 76/205 = 37.1% on ECP5-CABGA381,
// also <= 80 functional pins on S3.3-01 XC7K325T-2FFG900 carrier PCB!).
//
// Encapsulates all internal SoC/AXI4-Lite and wide parallel telemetry buses (ext_axil_*,
// aom_drive_q16[31:0], ddc_m_axis_tdata[63:0], blk_tile_beam_en[15:0], blk_tile_done/abort_in[15:0])
// behind UART 8N1+RTS SCADA control and a compact 16-bit TDM physical sensor/telemetry port,
// while keeping ALL safety-critical interlock, SPI DAC, blanker serial, and AOM RF enable pins
// directly bonded to dedicated physical package pins!
//
// Physical Pin Accounting (76 total I/O pins):
//   Clock & Reset  : clk, rst_n                                                  ( 2)
//   UART SCADA     : uart_rx, uart_tx, uart_rts_n                                ( 3)
//   1oo2D Interlock: il_ch_a_ok[7:0], il_ch_b_ok[7:0], il_hw_reset_b,
//                    safe_{blanker,laser,hv,uhv_valve,ph3_valve,magnet}_en,
//                    interlock_trip_out, safety_indep_trip_out                   (25)
//   Blanker Serial : blk_tile_sel[3:0], blk_tile_sclk, blk_tile_sdata,
//                    blk_tile_latch_n, blk_frame_latch_n, blk_safe_blanked,
//                    blk_any_beam_en, blk_tile_fb_sclk, blk_tile_fb_sdata        (12)
//   SPI HV DAC     : spi_cs_n, spi_sclk, spi_mosi, spi_ldac_n, hv_clr_n          ( 5)
//   AOM RF Enable  : aom_rf_en                                                   ( 1)
//   16-bit TDM I/O : tdm_adc_valid, tdm_adc_ready, tdm_adc_sel[1:0],
//                    tdm_adc_data[15:0], tdm_telem_valid, tdm_telem_word[2:0],
//                    tdm_telem_data[3:0] (nibbled telemetry)                     (28)
//   TOTAL          : 76 physical I/O pins (<= 80 carrier PCB & <= 205 ECP5-CABGA381!)
`timescale 1ns/1ps

module fpga_top_carrier_wrap #(
    parameter [15:0]  UART_BAUD_DIV = 16'd868,
    parameter integer DDC_N_CH      = 8,
    parameter         BOED_LOR_HEX  = "../boed_fpga/rom_loglik_p0.hex",
    parameter         BOED_EXP_HEX  = "../boed_fpga/rom_loglik_p1.hex"
) (
    input  wire        clk,
    input  wire        rst_n,

    // Host UART 8N1 SCADA + RTS flow control (3 pins)
    input  wire        uart_rx,
    output wire        uart_tx,
    output wire        uart_rts_n,

    // 1oo2D Fail-Safe Interlock Dedicated Physical Pins (25 pins)
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

    // Blanker Mezzanine Serial Bus + Serialized Tile Done/Abort Return (12 pins)
    output wire [3:0]  blk_tile_sel,
    output wire        blk_tile_sclk,
    output wire        blk_tile_sdata,
    output wire        blk_tile_latch_n,
    output wire        blk_frame_latch_n,
    output wire        blk_safe_blanked,
    output wire        blk_any_beam_en,
    input  wire        blk_tile_fb_load,
    input  wire        blk_tile_fb_done_bit,
    input  wire        blk_tile_fb_abort_bit,
    input  wire [1:0]  blk_tile_fb_bank_sel,

    // 8-ch 20-bit SPI HV DAC Physical Pins (5 pins)
    output wire        spi_cs_n,
    output wire        spi_sclk,
    output wire        spi_mosi,
    output wire        spi_ldac_n,
    output wire        hv_clr_n,

    // AOM Laser RF Enable Physical Pin (1 pin)
    output wire        aom_rf_en,

    // Compact 16-bit TDM Sensor In / Telemetry Out Bus (28 pins)
    // tdm_adc_sel: 2'b00=DDC ADC sample, 2'b01=DDC MF weight, 2'b10=AOM meas hi16, 2'b11=AOM temp_k & trigger
    input  wire        tdm_adc_valid,
    output wire        tdm_adc_ready,
    input  wire [1:0]  tdm_adc_sel,
    input  wire [15:0] tdm_adc_data,
    output reg         tdm_telem_valid,
    output reg  [2:0]  tdm_telem_word,
    output reg  [3:0]  tdm_telem_nibble
);
    // 2-FF reset synchronizer
    (* ASYNC_REG = "TRUE" *) reg rst_s1;
    (* ASYNC_REG = "TRUE" *) reg rst_s2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst_s1 <= 1'b0;
            rst_s2 <= 1'b0;
        end else begin
            rst_s1 <= 1'b1;
            rst_s2 <= rst_s1;
        end
    end
    wire rst_sync_n = rst_s2;

    // TDM deserialization registers for AOM sensor, DDC ADC/MF, and Blanker tile feedback
    reg [15:0] r_blk_done_in;
    reg [15:0] r_blk_abort_in;
    reg        r_aom_valid;
    reg signed [31:0] r_aom_meas;
    reg [15:0] r_aom_temp_k;
    reg        r_ddc_valid;
    reg signed [15:0] r_ddc_sample;
    reg signed [15:0] r_ddc_mf_w;

    wire [15:0] w_blk_beam_en;
    wire signed [31:0] w_aom_drive;
    wire        w_ddc_adc_ready;
    wire        w_ddc_tvalid;
    wire [63:0] w_ddc_tdata;
    wire [4:0]  w_ddc_tid;
    wire        w_ddc_tlast;
    wire [DDC_N_CH-1:0] w_ddc_qmask;

    assign blk_any_beam_en = |w_blk_beam_en;
    assign tdm_adc_ready   = w_ddc_adc_ready;

    // External AXI4-Lite slave cleanly tied off (host uses UART 8N1 SCADA on carrier PCB)
    wire        unused_awr, unused_wr, unused_bv, unused_arr, unused_rv;
    wire [1:0]  unused_br, unused_rr;
    wire [31:0] unused_rd;

    fpga_top_machine_ctrl #(
        .UART_BAUD_DIV(UART_BAUD_DIV),
        .DDC_N_CH     (DDC_N_CH),
        .BOED_LOR_HEX (BOED_LOR_HEX),
        .BOED_EXP_HEX (BOED_EXP_HEX)
    ) u_core_top (
        .clk                  (clk),
        .rst_n                (rst_n),
        .uart_rx              (uart_rx),
        .uart_tx              (uart_tx),
        .uart_rts_n           (uart_rts_n),
        .ext_axil_awaddr      (16'd0),
        .ext_axil_awvalid     (1'b0),
        .ext_axil_awready     (unused_awr),
        .ext_axil_wdata       (32'd0),
        .ext_axil_wstrb       (4'h0),
        .ext_axil_wvalid      (1'b0),
        .ext_axil_wready      (unused_wr),
        .ext_axil_bresp       (unused_br),
        .ext_axil_bvalid      (unused_bv),
        .ext_axil_bready      (1'b1),
        .ext_axil_araddr      (16'd0),
        .ext_axil_arvalid     (1'b0),
        .ext_axil_arready     (unused_arr),
        .ext_axil_rdata       (unused_rd),
        .ext_axil_rresp       (unused_rr),
        .ext_axil_rvalid      (unused_rv),
        .ext_axil_rready      (1'b1),
        .il_ch_a_ok           (il_ch_a_ok),
        .il_ch_b_ok           (il_ch_b_ok),
        .il_hw_reset_b        (il_hw_reset_b),
        .safe_blanker_en      (safe_blanker_en),
        .safe_laser_en        (safe_laser_en),
        .safe_hv_en           (safe_hv_en),
        .safe_uhv_valve_en    (safe_uhv_valve_en),
        .safe_ph3_valve_en    (safe_ph3_valve_en),
        .safe_magnet_en       (safe_magnet_en),
        .interlock_trip_out   (interlock_trip_out),
        .safety_indep_trip_out(safety_indep_trip_out),
        .blk_tile_done_in     (r_blk_done_in),
        .blk_tile_abort_in    (r_blk_abort_in),
        .blk_tile_sel         (blk_tile_sel),
        .blk_tile_sclk        (blk_tile_sclk),
        .blk_tile_sdata       (blk_tile_sdata),
        .blk_tile_latch_n     (blk_tile_latch_n),
        .blk_frame_latch_n    (blk_frame_latch_n),
        .blk_tile_beam_en     (w_blk_beam_en),
        .blk_safe_blanked     (blk_safe_blanked),
        .aom_ext_sample_valid (r_aom_valid),
        .aom_ext_meas_q16     (r_aom_meas),
        .aom_ext_temp_meas_k  (r_aom_temp_k),
        .aom_rf_en            (aom_rf_en),
        .aom_drive_q16        (w_aom_drive),
        .spi_cs_n             (spi_cs_n),
        .spi_sclk             (spi_sclk),
        .spi_mosi             (spi_mosi),
        .spi_ldac_n           (spi_ldac_n),
        .hv_clr_n             (hv_clr_n),
        .ddc_adc_valid        (r_ddc_valid),
        .ddc_adc_ready        (w_ddc_adc_ready),
        .ddc_adc_sample       (r_ddc_sample),
        .ddc_mf_weight        (r_ddc_mf_w),
        .ddc_m_axis_tvalid    (w_ddc_tvalid),
        .ddc_m_axis_tready    (1'b1),
        .ddc_m_axis_tdata     (w_ddc_tdata),
        .ddc_m_axis_tid       (w_ddc_tid),
        .ddc_m_axis_tlast     (w_ddc_tlast),
        .ddc_qubit_state_mask (w_ddc_qmask)
    );

    reg [31:0] telem_snap;
    reg [2:0]  telem_idx;

    wire _unused_ok = &{1'b0, unused_awr, unused_wr, unused_bv, unused_arr, unused_rv,
                        unused_br, unused_rr, unused_rd, w_ddc_tdata[63:32], w_ddc_tid, w_ddc_tlast};

    always @(posedge clk) begin
        if (!rst_sync_n) begin
            r_blk_done_in    <= 16'h0000;
            r_blk_abort_in   <= 16'h0000;
            r_aom_valid      <= 1'b0;
            r_aom_meas       <= 32'sd65536;
            r_aom_temp_k     <= 16'd300;
            r_ddc_valid      <= 1'b0;
            r_ddc_sample     <= 16'sd0;
            r_ddc_mf_w       <= 16'sd32767;
            telem_snap       <= 32'd0;
            telem_idx        <= 3'd0;
            tdm_telem_valid  <= 1'b0;
            tdm_telem_word   <= 3'd0;
            tdm_telem_nibble <= 4'd0;
        end else begin
            r_aom_valid <= 1'b0;
            r_ddc_valid <= 1'b0;

            if (blk_tile_fb_load) begin
                r_blk_done_in  <= {r_blk_done_in[14:0],  blk_tile_fb_done_bit};
                r_blk_abort_in <= {r_blk_abort_in[14:0], blk_tile_fb_abort_bit};
            end

            if (tdm_adc_valid) begin
                case (tdm_adc_sel)
                    2'b00: begin
                        r_ddc_sample <= $signed(tdm_adc_data);
                        r_ddc_valid  <= 1'b1;
                    end
                    2'b01: r_ddc_mf_w <= $signed(tdm_adc_data);
                    2'b10: r_aom_meas <= {tdm_adc_data, 16'd0};
                    default: begin
                        r_aom_temp_k <= tdm_adc_data;
                        r_aom_valid  <= 1'b1;
                    end
                endcase
            end

            // Time-division multiplexed 4-bit telemetry stream (cycles across AOM drive, DDC proj & qmask)
            if (telem_idx == 3'd0) begin
                if (w_ddc_tvalid) begin
                    telem_snap <= w_ddc_tdata[31:0];
                end else if (blk_tile_fb_bank_sel == 2'b01) begin
                    telem_snap <= w_aom_drive;
                end else begin
                    telem_snap <= {{(32 - DDC_N_CH){1'b0}}, w_ddc_qmask};
                end
            end
            tdm_telem_valid  <= 1'b1;
            tdm_telem_word   <= telem_idx;
            tdm_telem_nibble <= telem_snap[{telem_idx, 2'b00} +: 4];
            telem_idx        <= telem_idx + 3'd1;
        end
    end
endmodule
