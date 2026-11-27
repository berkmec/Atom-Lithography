// tb_spi_dac_hv_ctrl.v - Self-checking 8-ch 20-bit SPI DAC HV & hv_safe_clamp TB
`timescale 1ns/1ps

module tb_spi_dac_hv_ctrl;
    localparam integer CLK_PERIOD_NS = 10; // 100 MHz

    reg        clk;
    reg        rst_n;
    reg        hv_safe_clamp;
    reg        ch_wr_en;
    reg [2:0]  ch_wr_addr;
    reg [19:0] ch_wr_data;
    reg [2:0]  ch_rd_addr;
    wire [19:0] ch_rd_data;
    reg        start_update;
    reg        update_all;
    reg [7:0]  ch_update_mask;
    reg [15:0] cfg_sclk_div;

    wire       spi_cs_n;
    wire       spi_sclk;
    wire       spi_mosi;
    wire       spi_ldac_n;
    wire       hv_clr_n;
    wire       busy;
    wire       done_sticky;
    wire       clamp_zero_seq_done;
    wire [3:0] cur_ch_out;
    wire [23:0] last_tx_frame;

    spi_dac_hv_ctrl dut (
        .clk                 (clk),
        .rst_n               (rst_n),
        .hv_safe_clamp       (hv_safe_clamp),
        .ch_wr_en            (ch_wr_en),
        .ch_wr_addr          (ch_wr_addr),
        .ch_wr_data          (ch_wr_data),
        .ch_rd_addr          (ch_rd_addr),
        .ch_rd_data          (ch_rd_data),
        .start_update        (start_update),
        .update_all          (update_all),
        .ch_update_mask      (ch_update_mask),
        .cfg_sclk_div        (cfg_sclk_div),
        .spi_cs_n            (spi_cs_n),
        .spi_sclk            (spi_sclk),
        .spi_mosi            (spi_mosi),
        .spi_ldac_n          (spi_ldac_n),
        .hv_clr_n            (hv_clr_n),
        .busy                (busy),
        .done_sticky         (done_sticky),
        .clamp_zero_seq_done (clamp_zero_seq_done),
        .cur_ch_out          (cur_ch_out),
        .last_tx_frame       (last_tx_frame)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    // Real SPI Mode-0 Slave DAC Bank Model (captures 24-bit frames + simultaneous LDAC_N)
    reg [23:0] slave_shreg;
    integer    slave_bit_cnt;
    reg [19:0] slave_input_reg [0:7];
    reg [19:0] slave_dac_out   [0:7];
    reg [7:0]  slave_rx_mask;
    integer    slave_frame_cnt;
    integer    slave_ldac_cnt;
    reg        prev_sclk;
    reg        prev_cs_n;
    reg        prev_ldac_n;
    integer    s_k;

    always @(posedge clk) begin
        if (!rst_n) begin
            slave_shreg     <= 24'd0;
            slave_bit_cnt   <= 0;
            slave_rx_mask   <= 8'h00;
            slave_frame_cnt <= 0;
            slave_ldac_cnt  <= 0;
            prev_sclk       <= 1'b0;
            prev_cs_n       <= 1'b1;
            prev_ldac_n     <= 1'b1;
            for (s_k = 0; s_k < 8; s_k = s_k + 1) begin
                slave_input_reg[s_k] <= 20'd0;
                slave_dac_out[s_k]   <= 20'd0;
            end
        end else begin
            prev_sclk   <= spi_sclk;
            prev_cs_n   <= spi_cs_n;
            prev_ldac_n <= spi_ldac_n;

            if (!spi_cs_n && prev_cs_n) begin
                // Falling CS_N starts fresh 24-bit frame
                slave_shreg   <= 24'd0;
                slave_bit_cnt <= 0;
            end
            if (!spi_cs_n && spi_sclk && !prev_sclk) begin
                // Rising SCLK samples MOSI (MSB-first)
                slave_shreg   <= {slave_shreg[22:0], spi_mosi};
                slave_bit_cnt <= slave_bit_cnt + 1;
            end
            if (spi_cs_n && !prev_cs_n) begin
                // Rising CS_N commits complete 24-bit frame
                if (slave_bit_cnt == 24 && slave_shreg[23] == 1'b0) begin
                    slave_input_reg[slave_shreg[22:20]] <= slave_shreg[19:0];
                    slave_rx_mask[slave_shreg[22:20]]   <= 1'b1;
                    slave_frame_cnt                     <= slave_frame_cnt + 1;
                end
            end
            if (!spi_ldac_n && prev_ldac_n) begin
                // Simultaneous LDAC_N latches all 8 DAC outputs at once!
                for (s_k = 0; s_k < 8; s_k = s_k + 1) begin
                    slave_dac_out[s_k] <= slave_input_reg[s_k];
                end
                slave_ldac_cnt <= slave_ldac_cnt + 1;
            end
        end
    end

    integer errors;
    integer c;
    reg [19:0] expected_codes [0:7];

    task write_ch(input [2:0] ch, input [19:0] code);
        begin
            @(negedge clk);
            ch_wr_addr = ch;
            ch_wr_data = code;
            ch_wr_en   = 1'b1;
            @(posedge clk);
            @(negedge clk);
            ch_wr_en   = 1'b0;
        end
    endtask

    initial begin
        errors         = 0;
        rst_n          = 1'b0;
        hv_safe_clamp  = 1'b0;
        ch_wr_en       = 1'b0;
        ch_wr_addr     = 3'd0;
        ch_wr_data     = 20'd0;
        ch_rd_addr     = 3'd0;
        start_update   = 1'b0;
        update_all     = 1'b0;
        ch_update_mask = 8'h00;
        cfg_sclk_div   = 16'd2;

        expected_codes[0] = 20'h12345;
        expected_codes[1] = 20'hABCDE;
        expected_codes[2] = 20'h55555;
        expected_codes[3] = 20'hFFFFF;
        expected_codes[4] = 20'h80001;
        expected_codes[5] = 20'h0F0F0;
        expected_codes[6] = 20'h7CAFE;
        expected_codes[7] = 20'hE1234;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        // 1. Load all 8 channels and verify CSR readback
        for (c = 0; c < 8; c = c + 1) begin
            write_ch(c[2:0], expected_codes[c]);
        end
        for (c = 0; c < 8; c = c + 1) begin
            @(negedge clk);
            ch_rd_addr = c[2:0];
            #1;
            if (ch_rd_data !== expected_codes[c]) begin
                $display("ERROR: ch_rd_data[%0d]=%h exp=%h", c, ch_rd_data, expected_codes[c]);
                errors = errors + 1;
            end
        end

        // 2. Selective 4-channel update (mask 8'b1010_0101 = ch 0,2,5,7) with sclk_div=2
        @(negedge clk);
        slave_frame_cnt = 0;
        slave_ldac_cnt  = 0;
        slave_rx_mask   = 8'h00;
        update_all      = 1'b0;
        ch_update_mask  = 8'b1010_0101;
        start_update    = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start_update    = 1'b0;

        wait (done_sticky == 1'b1);
        repeat (2) @(posedge clk);
        if (slave_frame_cnt != 4 || slave_rx_mask !== 8'b1010_0101 || slave_ldac_cnt != 1) begin
            $display("ERROR: selective update mismatch frames=%0d mask=%b ldac=%0d",
                     slave_frame_cnt, slave_rx_mask, slave_ldac_cnt);
            errors = errors + 1;
        end
        if (slave_dac_out[0] !== expected_codes[0] || slave_dac_out[2] !== expected_codes[2] ||
            slave_dac_out[5] !== expected_codes[5] || slave_dac_out[7] !== expected_codes[7] ||
            slave_dac_out[1] !== 20'd0) begin
            $display("ERROR: selective DAC outputs mismatch!");
            errors = errors + 1;
        end

        // 3. Full 8-channel synchronized update_all=1 with sclk_div=4
        @(negedge clk);
        cfg_sclk_div    = 16'd4;
        slave_frame_cnt = 0;
        slave_ldac_cnt  = 0;
        slave_rx_mask   = 8'h00;
        update_all      = 1'b1;
        start_update    = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start_update    = 1'b0;

        wait (done_sticky == 1'b1);
        repeat (2) @(posedge clk);
        if (slave_frame_cnt != 8 || slave_rx_mask !== 8'hFF || slave_ldac_cnt != 1) begin
            $display("ERROR: full 8-ch update mismatch frames=%0d mask=%b ldac=%0d",
                     slave_frame_cnt, slave_rx_mask, slave_ldac_cnt);
            errors = errors + 1;
        end
        for (c = 0; c < 8; c = c + 1) begin
            if (slave_dac_out[c] !== expected_codes[c]) begin
                $display("ERROR: ch[%0d] dac_out=%h exp=%h", c, slave_dac_out[c], expected_codes[c]);
                errors = errors + 1;
            end
        end

        // 4. FAULT INJECTION: assert hv_safe_clamp MID-TRANSFER!
        // Start a non-zero transfer, then inject hv_safe_clamp 15 clocks in
        @(negedge clk);
        cfg_sclk_div    = 16'd2;
        slave_frame_cnt = 0;
        slave_ldac_cnt  = 0;
        slave_rx_mask   = 8'h00;
        update_all      = 1'b1;
        start_update    = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start_update    = 1'b0;
        repeat (15) @(posedge clk);

        @(negedge clk);
        hv_safe_clamp = 1'b1;
        #1;
        if (hv_clr_n !== 1'b0) begin
            $display("ERROR: hv_clr_n did not drop LOW immediately on hv_safe_clamp!");
            errors = errors + 1;
        end

        // Attempt a forbidden non-zero write while hv_safe_clamp is active
        write_ch(3'd3, 20'hFFFFF);

        wait (clamp_zero_seq_done == 1'b1);
        repeat (2) @(posedge clk);

        if (slave_rx_mask !== 8'hFF || slave_ldac_cnt < 1) begin
            $display("ERROR: clamp zero-override did not update all 8 channels + LDAC!");
            errors = errors + 1;
        end
        for (c = 0; c < 8; c = c + 1) begin
            if (slave_dac_out[c] !== 20'h00000) begin
                $display("ERROR: ch[%0d] not zeroed by hv_safe_clamp! got=%h", c, slave_dac_out[c]);
                errors = errors + 1;
            end
        end
        if (last_tx_frame !== {1'b0, 3'd7, 20'h00000}) begin
            $display("ERROR: last_tx_frame after clamp=%h exp=%h",
                     last_tx_frame, {1'b0, 3'd7, 20'h00000});
            errors = errors + 1;
        end

        // 5. OBS-144 AD5791 Minimum t_CS_HIGH & t_LDAC Pulse-Width Check at cfg_sclk_div=1!
        @(negedge clk);
        hv_safe_clamp = 1'b0;
        repeat (4) @(posedge clk);
        write_ch(3'd0, 20'h11111);
        write_ch(3'd1, 20'h22222);
        @(negedge clk);
        cfg_sclk_div    = 16'd1; // Request illegal 10 ns div -> hardware MUST enforce >= 30 ns pulses!
        update_all      = 1'b0;
        ch_update_mask  = 8'h03;
        start_update    = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start_update    = 1'b0;

        // Measure LDAC_N low width and CS_N high width between ch0 and ch1
        begin : blk_pulse_check
            integer cs_hi_cyc, ldac_lo_cyc, seen_cs_hi, seen_ldac_lo;
            reg     prev_c, prev_l, active_c;
            cs_hi_cyc    = 0;
            ldac_lo_cyc  = 0;
            seen_cs_hi   = 0;
            seen_ldac_lo = 0;
            prev_c       = 1'b1;
            prev_l       = 1'b1;
            active_c     = 1'b0;
            while (!done_sticky) begin
                @(posedge clk);
                if (!spi_cs_n) active_c = 1'b1;
                if (active_c && spi_cs_n && !seen_cs_hi) begin
                    cs_hi_cyc = cs_hi_cyc + 1;
                end else if (active_c && !spi_cs_n && prev_c && cs_hi_cyc > 0) begin
                    seen_cs_hi = 1;
                end
                if (!spi_ldac_n) begin
                    ldac_lo_cyc  = ldac_lo_cyc + 1;
                    seen_ldac_lo = 1;
                end
                prev_c = spi_cs_n;
                prev_l = spi_ldac_n;
            end
            if (cs_hi_cyc < 3) begin
                $display("ERROR: OBS-144 t_CS_HIGH=%0d0 ns < 30 ns at cfg_sclk_div=1!", cs_hi_cyc);
                errors = errors + 1;
            end
            if (!seen_ldac_lo || ldac_lo_cyc < 3) begin
                $display("ERROR: OBS-144 t_LDAC=%0d0 ns < 30 ns at cfg_sclk_div=1!", ldac_lo_cyc);
                errors = errors + 1;
            end
        end

        $display("SPI_DAC_SUMMARY errors=%0d channels=8 selective_ok=1 full_sync_ldac_ok=1 hv_safe_clamp_zero_ok=1",
                 errors);
        if (errors == 0) begin
            $display("PASS: tb_spi_dac_hv_ctrl");
            $finish;
        end else begin
            $display("FAIL: tb_spi_dac_hv_ctrl (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
