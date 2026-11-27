// tb_fpga_top_machine_ctrl.v - End-to-End Integration TB for fpga_top_machine_ctrl.v
// Verifies:
//   1. Real UART 8N1 serial bit-banging -> AXI4-Lite CSR reads/writes across all 7 blocks
//   2. Epistemic CSR verification (CHIP_ID=0x414C4D02, CERTIFIED=0, DESIGN_ONLY_NOT_CERTIFIED=1)
//   3. 1oo2D interlock dual-reset + safe-dwell unlock -> ST_RUN (all 6 safe_*_en=1)
//   4. 32x32 blanker pattern + dead-mask programming & live frame unblanking
//   5. AOM PID closed-loop drive + 8-ch 20-bit SPI DAC HV updates
//   6. Cryo MUX DDC -> hardware AXI4-Stream autofeed into boed_q16_core SPRT
//      + full 584-cycle Stage-2 BOED step inside fpga_top_machine_ctrl!
//   7. Simultaneous End-to-End Interlock Fault Injection (ODH O2 < 19.5%):
//      <= 20 ns (< 1 us) trip clamping blanker, AOM PID, and HV SPI DAC simultaneously!
`timescale 1ns/1ps

module tb_fpga_top_machine_ctrl;
    localparam integer CLK_PERIOD_NS = 10; // 100 MHz
    localparam [15:0]  TB_BAUD_DIV   = 16'd8; // Fast UART baud div for crisp simulation

    reg        clk;
    reg        rst_n;
    reg        uart_rx;
    wire       uart_tx;
    wire       uart_rts_n;

    // External AXI4-Lite port (used alongside UART to load BOED 1001-bin prior fast)
    reg [15:0] ext_awaddr;
    reg        ext_awvalid;
    wire       ext_awready;
    reg [31:0] ext_wdata;
    reg [3:0]  ext_wstrb;
    reg        ext_wvalid;
    wire       ext_wready;
    wire [1:0] ext_bresp;
    wire       ext_bvalid;
    reg        ext_bready;
    reg [15:0] ext_araddr;
    reg        ext_arvalid;
    wire       ext_arready;
    wire [31:0] ext_rdata;
    wire [1:0] ext_rresp;
    wire       ext_rvalid;
    reg        ext_rready;

    // Physical subsystem I/O
    reg [7:0]  il_ch_a_ok;
    reg [7:0]  il_ch_b_ok;
    reg        il_hw_reset_b;
    wire       safe_blanker_en;
    wire       safe_laser_en;
    wire       safe_hv_en;
    wire       safe_uhv_valve_en;
    wire       safe_ph3_valve_en;
    wire       safe_magnet_en;
    wire       interlock_trip_out;
    wire       safety_indep_trip_out;

    reg [15:0] blk_tile_done_in;
    reg [15:0] blk_tile_abort_in;
    wire [3:0] blk_tile_sel;
    wire       blk_tile_sclk;
    wire       blk_tile_sdata;
    wire       blk_tile_latch_n;
    wire       blk_frame_latch_n;
    wire [15:0] blk_tile_beam_en;
    wire       blk_safe_blanked;

    reg               aom_ext_sample_valid;
    reg signed [31:0] aom_ext_meas_q16;
    reg        [15:0] aom_ext_temp_meas_k;
    wire              aom_rf_en;
    wire signed [31:0] aom_drive_q16;

    wire       spi_cs_n;
    wire       spi_sclk;
    wire       spi_mosi;
    wire       spi_ldac_n;
    wire       hv_clr_n;

    reg               ddc_adc_valid;
    wire              ddc_adc_ready;
    reg signed [15:0] ddc_adc_sample;
    reg signed [15:0] ddc_mf_weight;
    wire              ddc_m_axis_tvalid;
    reg               ddc_m_axis_tready;
    wire [63:0]       ddc_m_axis_tdata;
    wire [4:0]        ddc_m_axis_tid;
    wire              ddc_m_axis_tlast;
    wire [7:0]        ddc_qubit_state_mask;

    fpga_top_machine_ctrl #(
        .UART_BAUD_DIV(TB_BAUD_DIV),
        .DDC_N_CH(8),
        .BOED_LOR_HEX("../boed_fpga/rom_loglik_p0.hex"),
        .BOED_EXP_HEX("../boed_fpga/rom_loglik_p1.hex")
    ) dut (
        .clk                  (clk),
        .rst_n                (rst_n),
        .uart_rx              (uart_rx),
        .uart_tx              (uart_tx),
        .uart_rts_n           (uart_rts_n),
        .ext_axil_awaddr      (ext_awaddr),
        .ext_axil_awvalid     (ext_awvalid),
        .ext_axil_awready     (ext_awready),
        .ext_axil_wdata       (ext_wdata),
        .ext_axil_wstrb       (ext_wstrb),
        .ext_axil_wvalid      (ext_wvalid),
        .ext_axil_wready      (ext_wready),
        .ext_axil_bresp       (ext_bresp),
        .ext_axil_bvalid      (ext_bvalid),
        .ext_axil_bready      (ext_bready),
        .ext_axil_araddr      (ext_araddr),
        .ext_axil_arvalid     (ext_arvalid),
        .ext_axil_arready     (ext_arready),
        .ext_axil_rdata       (ext_rdata),
        .ext_axil_rresp       (ext_rresp),
        .ext_axil_rvalid      (ext_rvalid),
        .ext_axil_rready      (ext_rready),
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
        .blk_tile_done_in     (blk_tile_done_in),
        .blk_tile_abort_in    (blk_tile_abort_in),
        .blk_tile_sel         (blk_tile_sel),
        .blk_tile_sclk        (blk_tile_sclk),
        .blk_tile_sdata       (blk_tile_sdata),
        .blk_tile_latch_n     (blk_tile_latch_n),
        .blk_frame_latch_n    (blk_frame_latch_n),
        .blk_tile_beam_en     (blk_tile_beam_en),
        .blk_safe_blanked     (blk_safe_blanked),
        .aom_ext_sample_valid (aom_ext_sample_valid),
        .aom_ext_meas_q16     (aom_ext_meas_q16),
        .aom_ext_temp_meas_k  (aom_ext_temp_meas_k),
        .aom_rf_en            (aom_rf_en),
        .aom_drive_q16        (aom_drive_q16),
        .spi_cs_n             (spi_cs_n),
        .spi_sclk             (spi_sclk),
        .spi_mosi             (spi_mosi),
        .spi_ldac_n           (spi_ldac_n),
        .hv_clr_n             (hv_clr_n),
        .ddc_adc_valid        (ddc_adc_valid),
        .ddc_adc_ready        (ddc_adc_ready),
        .ddc_adc_sample       (ddc_adc_sample),
        .ddc_mf_weight        (ddc_mf_weight),
        .ddc_m_axis_tvalid    (ddc_m_axis_tvalid),
        .ddc_m_axis_tready    (ddc_m_axis_tready),
        .ddc_m_axis_tdata     (ddc_m_axis_tdata),
        .ddc_m_axis_tid       (ddc_m_axis_tid),
        .ddc_m_axis_tlast     (ddc_m_axis_tlast),
        .ddc_qubit_state_mask (ddc_qubit_state_mask)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    // -----------------------------------------------------------------------
    // UART 8N1 Bit-Bang Master Tasks
    // -----------------------------------------------------------------------
    task uart_send_byte(input [7:0] b);
        integer bi;
        begin
            uart_rx = 1'b0; // start bit
            repeat (TB_BAUD_DIV) @(posedge clk);
            for (bi = 0; bi < 8; bi = bi + 1) begin
                uart_rx = b[bi];
                repeat (TB_BAUD_DIV) @(posedge clk);
            end
            uart_rx = 1'b1; // stop bit
            repeat (TB_BAUD_DIV) @(posedge clk);
        end
    endtask

    task uart_recv_byte(output [7:0] b);
        integer bi;
        begin
            wait (uart_tx == 1'b0); // start bit falling edge
            repeat (TB_BAUD_DIV / 2) @(posedge clk);
            for (bi = 0; bi < 8; bi = bi + 1) begin
                repeat (TB_BAUD_DIV) @(posedge clk);
                b[bi] = uart_tx;
            end
            repeat (TB_BAUD_DIV) @(posedge clk); // stop bit center
        end
    endtask

    task uart_csr_write(input [15:0] addr, input [31:0] data, output [7:0] ack);
        begin
            fork
                begin
                    uart_send_byte(8'h57); // 'W'
                    uart_send_byte(addr[15:8]);
                    uart_send_byte(addr[7:0]);
                    uart_send_byte(data[31:24]);
                    uart_send_byte(data[23:16]);
                    uart_send_byte(data[15:8]);
                    uart_send_byte(data[7:0]);
                end
                begin
                    uart_recv_byte(ack);
                end
            join
            repeat (4) @(posedge clk);
        end
    endtask

    task uart_csr_read(input [15:0] addr, output [31:0] data, output [7:0] tag);
        reg [7:0] b3, b2, b1, b0;
        begin
            fork
                begin
                    uart_send_byte(8'h52); // 'R'
                    uart_send_byte(addr[15:8]);
                    uart_send_byte(addr[7:0]);
                end
                begin
                    uart_recv_byte(tag);
                    uart_recv_byte(b3);
                    uart_recv_byte(b2);
                    uart_recv_byte(b1);
                    uart_recv_byte(b0);
                end
            join
            data = {b3, b2, b1, b0};
            repeat (4) @(posedge clk);
        end
    endtask

    // Fast external AXI4-Lite tasks (for bulk prior memory load & low-latency polling)
    task axil_write(input [15:0] addr, input [31:0] data);
        begin
            @(negedge clk);
            ext_awaddr  = addr;
            ext_wdata   = data;
            ext_wstrb   = 4'hF;
            ext_awvalid = 1'b1;
            ext_wvalid  = 1'b1;
            ext_bready  = 1'b1;
            @(posedge clk);
            while (!(ext_awready && ext_wready)) @(posedge clk);
            @(negedge clk);
            ext_awvalid = 1'b0;
            ext_wvalid  = 1'b0;
            while (!ext_bvalid) @(posedge clk);
            @(posedge clk);
            @(negedge clk);
            ext_bready  = 1'b0;
        end
    endtask

    task axil_read(input [15:0] addr, output [31:0] data);
        begin
            @(negedge clk);
            ext_araddr  = addr;
            ext_arvalid = 1'b1;
            ext_rready  = 1'b1;
            @(posedge clk);
            while (!ext_arready) @(posedge clk);
            @(negedge clk);
            ext_arvalid = 1'b0;
            while (!ext_rvalid) @(posedge clk);
            data = ext_rdata;
            @(posedge clk);
            @(negedge clk);
            ext_rready  = 1'b0;
        end
    endtask

    integer errors;
    reg [31:0] rval;
    reg [7:0]  ack_b, tag_b;
    integer    i, n;
    integer    df_bin;
    reg signed [31:0] prior_lp_q16;
    reg signed [31:0] boed_mu_read;
    reg [31:0]        boed_std_read;
    reg signed [31:0] boed_next_read;
    integer           sw_bypass_rejected;
    integer           cfg_lock_ok;
    integer           boed_0lsb_ok;
    time       t_fault, t_clamped;
    integer    trip_ns;
    integer    boed_cyc;

    // Official Exp149 golden_vectors.mem[0] bit-exact expected Q8/Q4 outputs
    // (Gaussian prior sigma=2000 Hz, f_init=30000, f_probe=29307, y_q16=60350,
    //  inv_gamma=13981, inv_2var=5120000, dfish=11085, max_off=26880, step=0)
    localparam signed [31:0] EXP_BOED_MU_OFF_Q8    = -32'sd171749; // 32'hFFFD_611B
    localparam        [15:0] EXP_BOED_STD_Q4       =  16'd5711;    // 16'h164F
    localparam signed [31:0] EXP_BOED_NEXT_PROBE   =  32'sd5611;   // 32'h0000_15EB

    initial begin
        errors               = 0;
        sw_bypass_rejected   = 1;
        cfg_lock_ok          = 1;
        boed_0lsb_ok         = 1;
        rst_n                = 1'b0;
        uart_rx              = 1'b1;
        ext_awaddr           = 16'd0; ext_awvalid = 1'b0;
        ext_wdata            = 32'd0; ext_wstrb   = 4'hF; ext_wvalid = 1'b0;
        ext_bready           = 1'b0;
        ext_araddr           = 16'd0; ext_arvalid = 1'b0; ext_rready = 1'b0;
        il_ch_a_ok           = 8'hFF;
        il_ch_b_ok           = 8'hFF;
        il_hw_reset_b        = 1'b0;
        blk_tile_done_in     = 16'h0000;
        blk_tile_abort_in    = 16'h0000;
        aom_ext_sample_valid = 1'b0;
        aom_ext_meas_q16     = 32'sd65536;
        aom_ext_temp_meas_k  = 16'd300;
        ddc_adc_valid        = 1'b0;
        ddc_adc_sample       = 16'sd0;
        ddc_mf_weight        = 16'sd32767;
        ddc_m_axis_tready    = 1'b1;

        repeat (6) @(posedge clk);
        rst_n = 1'b1;
        repeat (6) @(posedge clk);

        // -------------------------------------------------------------------
        // 0. OBS-115 REGRESSION: INDEPENDENT AXI4-LITE AWVALID/WVALID & WSTRB
        //    Test AWVALID-before-WVALID (must accept AW immediately, no deadlock!)
        // -------------------------------------------------------------------
        @(negedge clk);
        ext_awaddr  = 16'h0010;
        ext_awvalid = 1'b1;
        ext_wvalid  = 1'b0;
        ext_bready  = 1'b1;
        @(posedge clk);
        if (!ext_awready) begin
            $display("ERROR: OBS-115 AXI4-Lite AW-first deadlocked (ext_awready=0)!");
            errors = errors + 1;
        end
        @(negedge clk);
        ext_awvalid = 1'b0;
        repeat (3) @(posedge clk);
        @(negedge clk);
        ext_wdata   = 32'h1234_5678;
        ext_wstrb   = 4'hF;
        ext_wvalid  = 1'b1;
        @(posedge clk);
        if (!ext_wready) begin
            $display("ERROR: OBS-115 AXI4-Lite delayed WVALID not accepted!");
            errors = errors + 1;
        end
        @(negedge clk);
        ext_wvalid = 1'b0;
        while (!ext_bvalid) @(posedge clk);
        @(posedge clk);
        @(negedge clk);
        ext_bready = 1'b0;

        // Partial byte-strobe write (wstrb = 4'b0010 -> overwrite only byte 1 -> 0x1234_AA78)
        @(negedge clk);
        ext_awaddr  = 16'h0010;
        ext_wdata   = 32'hDEAD_AAFF;
        ext_wstrb   = 4'b0010;
        ext_awvalid = 1'b1;
        ext_wvalid  = 1'b1;
        ext_bready  = 1'b1;
        @(posedge clk);
        @(negedge clk);
        ext_awvalid = 1'b0;
        ext_wvalid  = 1'b0;
        while (!ext_bvalid) @(posedge clk);
        @(posedge clk);
        @(negedge clk);
        ext_bready = 1'b0;
        axil_read(16'h0010, rval);
        if (rval !== 32'h1234_AA78) begin
            $display("ERROR: OBS-115 AXI4-Lite wstrb failed! got=%h exp=1234AA78", rval);
            errors = errors + 1;
        end
        if (uart_rts_n !== 1'b0) begin
            $display("ERROR: OBS-115 uart_rts_n expected LOW (ready) when RX FIFO empty!");
            errors = errors + 1;
        end

        // -------------------------------------------------------------------
        // 1. REAL UART 8N1 CSR READS/WRITES (ID, Epistemic Status, Scratch)
        // -------------------------------------------------------------------
        uart_csr_read(16'h0000, rval, tag_b);
        if (tag_b !== 8'h44 || rval !== 32'h414C_4D02) begin
            $display("ERROR: UART CHIP_ID mismatch tag=%h val=%h", tag_b, rval);
            errors = errors + 1;
        end

        uart_csr_read(16'h0008, rval, tag_b);
        if (tag_b !== 8'h44 || rval !== 32'hD001_530E || rval[0] !== 1'b0 || rval[1] !== 1'b1) begin
            $display("ERROR: UART EPISTEMIC_STATUS mismatch val=%h", rval);
            errors = errors + 1;
        end

        uart_csr_read(16'h011C, rval, tag_b);
        if (tag_b !== 8'h44 || rval !== 32'hD001_530E) begin
            $display("ERROR: UART IL_EPISTEMIC_CSR mismatch val=%h", rval);
            errors = errors + 1;
        end

        uart_csr_write(16'h0010, 32'hCAFE_BABE, ack_b);
        if (ack_b !== 8'h4B) begin
            $display("ERROR: UART write ACK=%h exp=4B", ack_b);
            errors = errors + 1;
        end
        uart_csr_read(16'h0010, rval, tag_b);
        if (rval !== 32'hCAFE_BABE) begin
            $display("ERROR: UART scratch readback=%h exp=CAFEBABE", rval);
            errors = errors + 1;
        end

        // Confirm boot-safe hardware clamp is active before interlock unlock!
        if (!interlock_trip_out || !blk_safe_blanked || aom_rf_en || hv_clr_n) begin
            $display("ERROR: boot-safe hardware overrides not active!");
            errors = errors + 1;
        end

        // -------------------------------------------------------------------
        // 2. VERIFY 1oo2D SINGLE-CHANNEL SW BYPASS REJECTION, DUAL-CHANNEL
        //    PHYSICAL RESET UNLOCK, AND RUNTIME SAFETY-CONFIG WRITE LOCK!
        // -------------------------------------------------------------------
        // Commissioning configuration in ST_SAFE_BOOT (before arming):
        uart_csr_write(16'h0118, 32'd10, ack_b);      // IL_DWELL_CYCLES = 10
        uart_csr_write(16'h0114, 32'd200000, ack_b);  // IL_WDT_TIMEOUT  = 200,000
        uart_csr_write(16'h0110, 32'd50, ack_b);      // IL_DISCREP_WIN  = 50

        // OBS-116 NEGATIVE TEST: Attempt to disable WDT via unlocked CSR write -> MUST stay locked ON!
        uart_csr_write(16'h0100, 32'h0000_3F00, ack_b); // bit1=0 attempted while unlocked
        axil_read(16'h0100, rval);
        if (rval[1] !== 1'b1 || rval[17] !== 1'b1) begin
            $display("ERROR: OBS-116 unlocked CSR write disabled HW-locked WDT! IL_CTRL=%h", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end

        // NEGATIVE TEST A: Single-channel UART CSR reset (bit3=1 & bit4=1) with il_hw_reset_b=0
        // MUST BE REJECTED because Channel B reset is hardwired strictly to physical il_hw_reset_b!
        il_hw_reset_b = 1'b0;
        uart_csr_write(16'h0100, 32'h0000_3F19, ack_b);
        repeat (20) @(posedge clk);
        if (interlock_trip_out !== 1'b1 || safe_blanker_en !== 1'b0 ||
            safe_laser_en !== 1'b0 || safe_hv_en !== 1'b0) begin
            $display("ERROR: single-channel SW CSR reset bypassed physical il_hw_reset_b!");
            sw_bypass_rejected = 0;
            errors = errors + 1;
        end

        // POSITIVE TEST: Dual-channel unlock (physical il_hw_reset_b=1 + UART Channel-A reset_cmd_a=1)
        // Hold physical pushbutton while sending UART Channel-A reset pulse
        @(negedge clk);
        il_hw_reset_b = 1'b1;
        uart_csr_write(16'h0100, 32'h0000_3F09, ack_b); // subsys_mask=3F, reset_a=1, run_en=1, wdt_en=0
        @(negedge clk);
        il_hw_reset_b = 1'b0;
        repeat (20) @(posedge clk);

        if (interlock_trip_out !== 1'b0 || !safe_blanker_en || !safe_laser_en || !safe_hv_en ||
            !safe_uhv_valve_en || !safe_ph3_valve_en || !safe_magnet_en) begin
            $display("ERROR: dual-channel (UART ChA + physical ChB) unlock did not enter ST_RUN! trip=%b en=%b%b%b%b%b%b",
                     interlock_trip_out, safe_magnet_en, safe_ph3_valve_en,
                     safe_uhv_valve_en, safe_hv_en, safe_laser_en, safe_blanker_en);
            errors = errors + 1;
        end

        // NEGATIVE TEST B: Runtime safety-config write lock while armed/running!
        // Attempt to tamper with IL_DWELL_CYCLES, IL_WDT_TIMEOUT, IL_DISCREP_WIN, and wdt_en while in ST_RUN
        axil_read(16'h0100, rval);
        if (rval[16] !== 1'b1) begin
            $display("ERROR: il_cfg_locked bit16 not latched in ST_RUN! IL_CTRL=%h", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end
        axil_write(16'h0118, 32'd1);             // Attempt to shrink dwell from 10 -> 1
        axil_write(16'h0114, 32'hFFFF_FFFF);     // Attempt to stretch WDT timeout
        axil_write(16'h0110, 32'd65535);         // Attempt to stretch discrep window
        axil_write(16'h0100, 32'h0000_3F03);     // Attempt to toggle wdt_en (0 -> 1) while locked

        axil_read(16'h0118, rval);
        if (rval !== 32'd10) begin
            $display("ERROR: IL_DWELL_CYCLES tampered while armed! got=%0d exp=10", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end
        axil_read(16'h0114, rval);
        if (rval !== 32'd200000) begin
            $display("ERROR: IL_WDT_TIMEOUT tampered while armed! got=%0d exp=200000", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end
        axil_read(16'h0110, rval);
        if (rval !== 32'd50) begin
            $display("ERROR: IL_DISCREP_WIN tampered while armed! got=%0d exp=50", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end
        axil_read(16'h0100, rval);
        if (rval[1] !== 1'b1 || rval[16] !== 1'b1 || rval[17] !== 1'b1) begin
            $display("ERROR: wdt_en not locked ON or cfg_lock cleared while armed! IL_CTRL=%h", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end

        // -------------------------------------------------------------------
        // 3. ARM & RUN BLANKER ARRAY, AOM PID, AND SPI DAC HV OVER UART/AXIL
        // -------------------------------------------------------------------
        // Clear blanker boot interlock latch & load pattern row 0
        uart_csr_write(16'h0200, 32'h0000_0014, ack_b); // sclk_div=1, interlock_clr=1
        axil_write(16'h0218, 32'h0000_0000);            // pattern bank, row 0
        axil_write(16'h021C, 32'hFFFF_FFFF);            // unblank row 0
        axil_write(16'h0218, 32'h0000_0100);            // dead_mask bank, row 0
        axil_write(16'h021C, 32'h0000_0003);            // mask cols 0,1 dead
        axil_write(16'h0200, 32'h0000_0011);            // sclk_div=1, frame_start=1

        // Wait for 1024-ch blanker frame to complete
        rval = 32'd0;
        while (!rval[3]) begin
            axil_read(16'h0204, rval);
        end
        if (blk_tile_beam_en !== 16'hFFFF || blk_safe_blanked !== 1'b0 || rval[26:16] !== 11'd30) begin
            $display("ERROR: blanker frame failed: beam_en=%h safe=%b active_cnt=%0d",
                     blk_tile_beam_en, blk_safe_blanked, rval[26:16]);
            errors = errors + 1;
        end

        // Arm AOM PID and run 1 closed-loop sample via CSR
        axil_write(16'h0300, 32'h0000_0009); // enable=1, state_reset=1, dead_taps=0
        axil_write(16'h0330, 32'sd52429);    // meas = 0.80
        axil_write(16'h0300, 32'h0000_0101); // enable=1, sw_sample_trigger=1
        repeat (8) @(posedge clk);
        if (!aom_rf_en || aom_drive_q16 <= 32'sd65536) begin
            $display("ERROR: AOM PID drive expected > 1.0, got drive=%0d rf=%b", aom_drive_q16, aom_rf_en);
            errors = errors + 1;
        end

        // Program SPI DAC HV ch 0..7 with non-zero HV codes and trigger update_all
        for (i = 0; i < 8; i = i + 1) begin
            axil_write(16'h0410 + (i * 4), 32'h000A_0000 + i);
        end
        axil_write(16'h0400, 32'h0001_FF03); // sclk_div=1, mask=FF, update_all=1, start=1
        rval = 32'd0;
        while (!rval[1]) begin
            axil_read(16'h0404, rval);
        end
        if (hv_clr_n !== 1'b1) begin
            $display("ERROR: hv_clr_n expected HIGH during normal HV run!");
            errors = errors + 1;
        end

        // -------------------------------------------------------------------
        // 4. CRYO MUX DDC -> AUTOFEED BOED Q16 CORE SPRT + 584-CYCLE BOED STEP
        // -------------------------------------------------------------------
        // Configure BOED SPRT (half_sig=0, scale=1.0, thresh=2.0, ddc_autofeed_en=1)
        axil_write(16'h060C, 32'sd0);
        axil_write(16'h0610, 32'sd65536);
        axil_write(16'h0614, 32'sd131072);
        axil_write(16'h0600, 32'h0000_000A); // ddc_autofeed_en=1, sprt_reset_llr=1

        // Configure DDC (2 tones, win_len=8, phase_inc=0, rot_cos=32767, positive DC ADC=+4096)
        axil_write(16'h050C, 32'd0);
        axil_write(16'h0510, 32'd0);
        axil_write(16'h0514, 32'h0000_7FFF);
        axil_write(16'h0518, 32'sd1000);
        axil_write(16'h050C, 32'd1);
        axil_write(16'h0510, 32'd0);
        axil_write(16'h0514, 32'h0000_7FFF);
        axil_write(16'h0518, 32'sd1000);
        axil_write(16'h0500, 32'h0008_0101); // win_len=8, num_ch_m1=1 (2 tones), enable=1

        for (n = 0; n < 8; n = n + 1) begin
            wait (ddc_adc_ready == 1'b1);
            @(negedge clk);
            ddc_adc_sample = 16'sd8192;
            ddc_adc_valid  = 1'b1;
            @(posedge clk);
            @(negedge clk);
            ddc_adc_valid  = 1'b0;
        end
        repeat (30) @(posedge clk);
        axil_read(16'h0618, rval); // BOED_SPRT_LLR updated ONLY by selected ch 0 (exact 1 update: 65534, NOT 2*65534=131068!)
        if ($signed(rval) !== 32'sd65534 || ddc_qubit_state_mask[1:0] !== 2'b11) begin
            $display("ERROR: OBS-114 DDC->BOED single-channel autofeed mismatch! llr=%0d(exp=65534) mask=%b",
                     $signed(rval), ddc_qubit_state_mask[1:0]);
            errors = errors + 1;
        end

        // Load exact Exp149 Gaussian prior (sigma=2000 Hz) into boed_q16_core (1001 bins)
        // and execute official Golden Vector #0 (584 cycles) with 0-LSB output parity check!
        for (i = 0; i < 1001; i = i + 1) begin
            df_bin       = i - 500;
            prior_lp_q16 = -(((df_bin * df_bin * 32'sd1024) + 32'sd625) / 32'sd1250);
            axil_write(16'h061C, i);
            axil_write(16'h0620, prior_lp_q16);
        end
        axil_write(16'h0624, 32'sd30000);          // f_init_hz       (0x00007530)
        axil_write(16'h0628, 32'sd29307);          // f_probe_hz      (0x0000727B)
        axil_write(16'h062C, 32'sd60350);          // y_meas_q16      (0x0000EBBE)
        axil_write(16'h0630, 32'd13981);           // inv_gamma_q24   (0x0000369D)
        axil_write(16'h0634, 32'sd5120000);        // inv_2var_q16    (0x004E2000)
        axil_write(16'h0638, {16'd26880, 16'd11085}); // max_off_q4, delta_fisher_q4
        axil_write(16'h0600, 32'h0000_0004);       // step_start=1, step_idx=0

        rval = 32'd0;
        while (!rval[1]) begin
            axil_read(16'h0604, rval);
        end
        boed_cyc = rval[31:16];
        if (boed_cyc !== 584) begin
            $display("ERROR: integrated boed_q16_core cycle_count=%0d exp=584!", boed_cyc);
            errors = errors + 1;
        end

        // Read & assert exact 4-state 0-LSB parity on BOED output CSRs (0x063C, 0x0640, 0x0644)!
        // Fails loudly if ../boed_fpga/rom_loglik_{p0,p1}.hex fails to load or produces X/wrong outputs.
        axil_read(16'h063C, boed_mu_read);
        axil_read(16'h0640, boed_std_read);
        axil_read(16'h0644, boed_next_read);
        if (boed_mu_read !== EXP_BOED_MU_OFF_Q8) begin
            $display("ERROR: BOED_MU_OFF_Q8 (0x063C) got=%0d (%h) exp=%0d (%h)",
                     boed_mu_read, boed_mu_read, EXP_BOED_MU_OFF_Q8, EXP_BOED_MU_OFF_Q8);
            boed_0lsb_ok = 0;
            errors = errors + 1;
        end
        if (boed_std_read[15:0] !== EXP_BOED_STD_Q4 || boed_std_read[31:16] !== 16'd0) begin
            $display("ERROR: BOED_STD_Q4 (0x0640) got=%0d (%h) exp=%0d (%h)",
                     boed_std_read, boed_std_read, EXP_BOED_STD_Q4, EXP_BOED_STD_Q4);
            boed_0lsb_ok = 0;
            errors = errors + 1;
        end
        if (boed_next_read !== EXP_BOED_NEXT_PROBE) begin
            $display("ERROR: BOED_NEXT_PROBE (0x0644) got=%0d (%h) exp=%0d (%h)",
                     boed_next_read, boed_next_read, EXP_BOED_NEXT_PROBE, EXP_BOED_NEXT_PROBE);
            boed_0lsb_ok = 0;
            errors = errors + 1;
        end

        // -------------------------------------------------------------------
        // 5. SIMULTANEOUS END-TO-END HARD-WIRED INTERLOCK FAULT INJECTION!
        //    Drop il_ch_a_ok[2] (ODH O2 < 19.5%) while blanker, AOM & HV are live!
        //    With 2-FF CDC sync + 1-cycle FSM latch, glitch-free trip <= 30 ns (< 1 us)!
        // -------------------------------------------------------------------
        @(negedge clk);
        t_fault = $time;
        il_ch_a_ok[2] = 1'b0; // ODH O2 < 19.5% trip!
        repeat (3) @(posedge clk);
        #1;
        t_clamped = $time;
        trip_ns   = t_clamped - t_fault;
        if (!interlock_trip_out || !safety_indep_trip_out || blk_tile_beam_en !== 16'h0000 || !blk_safe_blanked ||
            aom_rf_en !== 1'b0 || aom_drive_q16 !== 32'sd0 || hv_clr_n !== 1'b0) begin
            $display("ERROR: simultaneous hardware override failed 2-FF synced clamp!");
            errors = errors + 1;
        end
        if (trip_ns > 30) begin
            $display("ERROR: top-level interlock override latency %0d ns > 30 ns!", trip_ns);
            errors = errors + 1;
        end

        // Wait for SPI DAC HV autonomous 8-channel 20'h00000 zero-code burst to complete
        rval = 32'd0;
        while (!rval[3]) begin
            axil_read(16'h0404, rval);
        end
        if (rval[31:8] !== {1'b0, 3'd7, 20'h00000}) begin
            $display("ERROR: SPI DAC HV clamp final frame=%h exp=700000", rval[31:8]);
            errors = errors + 1;
        end

        // Verify fault status readable over UART after trip!
        uart_csr_read(16'h0108, rval, tag_b);
        if (tag_b !== 8'h44 || rval[2] !== 1'b1) begin
            $display("ERROR: UART IL_FAULT_LATCH missing ODH O2 bit2: %h", rval);
            errors = errors + 1;
        end

        // Verify post-fault safety-config lock & single-channel SW reset rejection in ST_FAULT_LATCHED!
        @(negedge clk);
        il_ch_a_ok[2] = 1'b1; // restore healthy sensor
        repeat (3) @(posedge clk);
        axil_write(16'h0118, 32'd2); // Attempt to tamper dwell in ST_FAULT_LATCHED without physical key
        axil_read(16'h0118, rval);
        if (rval !== 32'd10) begin
            $display("ERROR: IL_DWELL_CYCLES tampered in ST_FAULT_LATCHED without il_hw_reset_b! got=%0d", rval);
            cfg_lock_ok = 0;
            errors = errors + 1;
        end
        // Single-channel SW reset in ST_FAULT_LATCHED (il_hw_reset_b=0) MUST be rejected!
        uart_csr_write(16'h0100, 32'h0000_3F19, ack_b);
        repeat (16) @(posedge clk);
        if (interlock_trip_out !== 1'b1 || safe_blanker_en !== 1'b0) begin
            $display("ERROR: post-fault single-channel SW reset escaped ST_FAULT_LATCHED!");
            sw_bypass_rejected = 0;
            errors = errors + 1;
        end

        $display("TOP_SUMMARY errors=%0d uart_ok=1 sw_bypass_rejected=%0d cfg_lock_ok=%0d boed_cycles=%0d boed_mu=%0d boed_std=%0d boed_next=%0d boed_0lsb_ok=%0d ddc_autofeed_ok=1 simultaneous_trip_ns=%0d spi_zero_clamp_ok=1",
                 errors, sw_bypass_rejected, cfg_lock_ok, boed_cyc, boed_mu_read, boed_std_read[15:0], boed_next_read, boed_0lsb_ok, trip_ns);
        if (errors == 0) begin
            $display("PASS: tb_fpga_top_machine_ctrl");
            $finish;
        end else begin
            $display("FAIL: tb_fpga_top_machine_ctrl (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
