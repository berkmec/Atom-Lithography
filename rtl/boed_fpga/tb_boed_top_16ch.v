// tb_boed_top_16ch.v - Multi-Channel AXI4-Stream Integration Testbench for boed_top_16ch
// Verifies concurrent multi-channel execution across 4 distinct physical regimes (clean,
// crowded doublet, edge-of-grid left, zero-signal) on channels 0, 5, 11, 15, AXI4-Stream
// tready backpressure, priority-arbiter output framing, and Stage-0 SPRT packet routing.
`timescale 1ns/1ps

module tb_boed_top_16ch;
    localparam integer N_BINS = 1001;

    reg                clk;
    reg                rst_n;

    reg         [31:0] cfg_inv_gamma_q24;
    reg  signed [31:0] cfg_inv_2var_q16;
    reg         [15:0] cfg_delta_fisher_q4;
    reg         [15:0] cfg_max_off_q4;
    reg  signed [31:0] cfg_sprt_half_sig_q16;
    reg  signed [31:0] cfg_sprt_scale_q16;
    reg  signed [31:0] cfg_sprt_thresh_q16;

    reg                prior_load_en;
    reg         [3:0]  prior_load_ch;
    reg         [9:0]  prior_load_addr;
    reg  signed [31:0] prior_load_lp_q16;

    reg                s_axis_tvalid;
    wire               s_axis_tready;
    reg        [127:0] s_axis_tdata;
    reg         [3:0]  s_axis_tid;
    reg                s_axis_tlast;

    wire               m_axis_tvalid;
    reg                m_axis_tready;
    wire        [95:0] m_axis_tdata;
    wire        [3:0]  m_axis_tid;
    wire               m_axis_tlast;

    wire        [15:0] ch_busy_mask;
    wire        [15:0] ch_sprt_donor_mask;

    initial clk = 1'b0;
    always #2 clk = ~clk;

    boed_top_16ch dut (
        .clk                   (clk),
        .rst_n                 (rst_n),
        .cfg_inv_gamma_q24     (cfg_inv_gamma_q24),
        .cfg_inv_2var_q16      (cfg_inv_2var_q16),
        .cfg_delta_fisher_q4   (cfg_delta_fisher_q4),
        .cfg_max_off_q4        (cfg_max_off_q4),
        .cfg_sprt_half_sig_q16 (cfg_sprt_half_sig_q16),
        .cfg_sprt_scale_q16    (cfg_sprt_scale_q16),
        .cfg_sprt_thresh_q16   (cfg_sprt_thresh_q16),
        .prior_load_en         (prior_load_en),
        .prior_load_ch         (prior_load_ch),
        .prior_load_addr       (prior_load_addr),
        .prior_load_lp_q16     (prior_load_lp_q16),
        .s_axis_tvalid         (s_axis_tvalid),
        .s_axis_tready         (s_axis_tready),
        .s_axis_tdata          (s_axis_tdata),
        .s_axis_tid            (s_axis_tid),
        .s_axis_tlast          (s_axis_tlast),
        .m_axis_tvalid         (m_axis_tvalid),
        .m_axis_tready         (m_axis_tready),
        .m_axis_tdata          (m_axis_tdata),
        .m_axis_tid            (m_axis_tid),
        .m_axis_tlast          (m_axis_tlast),
        .ch_busy_mask          (ch_busy_mask),
        .ch_sprt_donor_mask    (ch_sprt_donor_mask)
    );

    reg [287:0] vec_mem [0:63];
    // Test 4 trajectories that share default calibration (gamma=1200 Hz, sigma_n=0.08):
    //   vec  0: clean_neg  -> ch 0
    //   vec 16: crowded    -> ch 5
    //   vec 24: edge_left  -> ch 11
    //   vec 48: zero_sig   -> ch 15
    reg [3:0]   test_ch  [0:3];
    integer     test_vec [0:3];
    reg [3:0]   got_mask;

    integer k, b, df_hz, cyc, rx_count, errors;
    reg signed [31:0] got_mu, got_next, exp_mu, exp_next;
    reg        [15:0] got_std, got_cyc, exp_std;

    initial begin
        $readmemh("golden_vectors.mem", vec_mem);

        test_ch[0]  = 4'd0;  test_vec[0] = 0;
        test_ch[1]  = 4'd5;  test_vec[1] = 16;
        test_ch[2]  = 4'd11; test_vec[2] = 24;
        test_ch[3]  = 4'd15; test_vec[3] = 48;

        rst_n                 = 1'b0;
        cfg_inv_gamma_q24     = vec_mem[0][191:160];
        cfg_inv_2var_q16      = vec_mem[0][159:128];
        cfg_delta_fisher_q4   = vec_mem[0][127:112];
        cfg_max_off_q4        = vec_mem[0][111:96];
        cfg_sprt_half_sig_q16 = 32'sd13107;
        cfg_sprt_scale_q16    = 32'sd1820444;
        cfg_sprt_thresh_q16   = 32'sd301466;

        prior_load_en         = 1'b0;
        prior_load_ch         = 4'd0;
        prior_load_addr       = 10'd0;
        prior_load_lp_q16     = 32'sd0;
        s_axis_tvalid         = 1'b0;
        s_axis_tdata          = 128'd0;
        s_axis_tid            = 4'd0;
        s_axis_tlast          = 1'b0;
        m_axis_tready         = 1'b1;
        got_mask              = 4'd0;
        rx_count              = 0;
        errors                = 0;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk);

        // Load Gaussian prior into all 4 selected channels
        for (k = 0; k < 4; k = k + 1) begin
            prior_load_ch = test_ch[k];
            for (b = 0; b < N_BINS; b = b + 1) begin
                df_hz             = b - 500;
                prior_load_en     = 1'b1;
                prior_load_addr   = b[9:0];
                prior_load_lp_q16 = -(((df_hz * df_hz * 32'sd1024) + 32'sd625) / 32'sd1250);
                @(negedge clk);
            end
        end
        prior_load_en = 1'b0;
        @(negedge clk);

        // Launch all 4 channels concurrently on consecutive clock cycles (same-cycle arrival stress)
        for (k = 0; k < 4; k = k + 1) begin
            s_axis_tvalid = 1'b1;
            s_axis_tid    = test_ch[k];
            s_axis_tlast  = 1'b1;
            s_axis_tdata  = {
                22'd0,
                1'b0, // sprt_reset
                1'b0, // sprt_mode
                vec_mem[test_vec[k]][95:88],   // step_idx
                vec_mem[test_vec[k]][287:256], // f_init_hz
                vec_mem[test_vec[k]][223:192], // y_meas_q16
                vec_mem[test_vec[k]][255:224]  // f_probe_hz
            };
            #1;
            if (!s_axis_tready) begin
                $display("FAIL_TOP16: channel %0d unexpectedly not ready", test_ch[k]);
                errors = errors + 1;
            end
            @(negedge clk);
        end
        s_axis_tvalid = 1'b0;

        // Verify busy backpressure when addressing busy channel 0
        s_axis_tid = 4'd0;
        #1;
        if (s_axis_tready !== 1'b0 || ch_busy_mask[0] !== 1'b1 || ch_busy_mask[15] !== 1'b1) begin
            $display("FAIL_TOP16: expected backpressure on busy ch0/ch15, tready=%b busy=%h",
                     s_axis_tready, ch_busy_mask);
            errors = errors + 1;
        end

        // Also send a Stage-0 SPRT packet on idle channel 3 while BOED channels are running
        @(negedge clk);
        s_axis_tvalid = 1'b1;
        s_axis_tid    = 4'd3;
        s_axis_tlast  = 1'b1;
        s_axis_tdata  = {22'd0, 1'b0, 1'b1, 8'd0, 32'sd0, 32'sd32768, 32'sd0}; // y=+0.5 > 0.2
        @(negedge clk);
        s_axis_tvalid = 1'b0;

        // Collect all 4 AXI4-Stream completion frames
        cyc = 0;
        while (rx_count < 4 && cyc < 700) begin
            @(negedge clk);
            cyc = cyc + 1;
            if (m_axis_tvalid && m_axis_tready) begin
                got_mu   = m_axis_tdata[31:0];
                got_std  = m_axis_tdata[47:32];
                got_next = m_axis_tdata[79:48];
                got_cyc  = m_axis_tdata[95:80];

                for (k = 0; k < 4; k = k + 1) begin
                    if (m_axis_tid == test_ch[k]) begin
                        got_mask[k] = 1'b1;
                        exp_std  = vec_mem[test_vec[k]][79:64];
                        exp_mu   = vec_mem[test_vec[k]][63:32];
                        exp_next = vec_mem[test_vec[k]][31:0];
                        if (got_mu !== exp_mu || got_std !== exp_std || got_next !== exp_next ||
                            got_cyc !== 16'd584 || m_axis_tlast !== 1'b1) begin
                            $display("FAIL_TOP16 ch=%0d mu=%0d(exp=%0d) std=%0d(exp=%0d) next=%0d(exp=%0d) cyc=%0d",
                                     m_axis_tid, got_mu, exp_mu, got_std, exp_std, got_next, exp_next, got_cyc);
                            errors = errors + 1;
                        end
                    end
                end
                rx_count = rx_count + 1;
            end
        end

        if (rx_count !== 4 || got_mask !== 4'b1111) begin
            $display("FAIL_TOP16: rx_count=%0d got_mask=%b", rx_count, got_mask);
            errors = errors + 1;
        end
        if (ch_sprt_donor_mask[3] !== 1'b1) begin
            $display("FAIL_TOP16: ch3 SPRT donor_present expected 1, got %b", ch_sprt_donor_mask[3]);
            errors = errors + 1;
        end

        $display("TOP16_SUMMARY channels_verified=%0d errors=%0d sprt_ch3_donor=%0d",
                 rx_count, errors, ch_sprt_donor_mask[3]);

        if (errors == 0) begin
            $display("PASS: boed_top_16ch AXI4-Stream 4-channel concurrent + SPRT verified at 0 LSB / 584 cycles!");
        end else begin
            $display("FAIL: boed_top_16ch errors=%0d", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
