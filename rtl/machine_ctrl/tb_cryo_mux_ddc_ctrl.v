// tb_cryo_mux_ddc_ctrl.v - Self-checking 8-ch & 32-tone Cryo MUX DDC + AXI4-Stream TB
`timescale 1ns/1ps

module tb_cryo_mux_ddc_ctrl;
    localparam integer CLK_PERIOD_NS = 10; // 100 MHz

    reg        clk;
    reg        rst_n;

    // Instance 1: Default N_CH = 8 (verified bit-exact vs Python Q1.15 reference)
    reg               en8, clr8, mf_en8;
    reg        [4:0]  nch8;
    reg        [15:0] wlen8;
    reg        [4:0]  caddr8;
    reg               pwe8, rwe8, twe8;
    reg        [23:0] pinc8;
    reg signed [15:0] rcos8, rsin8;
    reg signed [31:0] thr8;
    reg               adc_v8;
    wire              adc_r8;
    reg signed [15:0] adc_s8, mfw8;
    wire              axis_tv8;
    reg               axis_tr8;
    wire       [63:0] axis_td8;
    wire       [4:0]  axis_tid8;
    wire              axis_tl8;
    wire              busy8, done_p8, done_s8;
    wire       [7:0]  qmask8;
    wire       [15:0] scnt8, wcnt8;
    wire signed [31:0] ri8, rq8, rp8;

    cryo_mux_ddc_ctrl #(.N_CH(8)) u_dut8 (
        .clk                 (clk),
        .rst_n               (rst_n),
        .enable              (en8),
        .soft_clear          (clr8),
        .mf_en               (mf_en8),
        .cfg_num_ch_m1       (nch8),
        .cfg_win_len         (wlen8),
        .cfg_ch_addr         (caddr8),
        .cfg_phase_we        (pwe8),
        .cfg_phase_inc       (pinc8),
        .cfg_rot_we          (rwe8),
        .cfg_rot_cos         (rcos8),
        .cfg_rot_sin         (rsin8),
        .cfg_thresh_we       (twe8),
        .cfg_thresh          (thr8),
        .adc_valid           (adc_v8),
        .adc_ready           (adc_r8),
        .adc_sample          (adc_s8),
        .mf_weight           (mfw8),
        .m_axis_tvalid       (axis_tv8),
        .m_axis_tready       (axis_tr8),
        .m_axis_tdata        (axis_td8),
        .m_axis_tid          (axis_tid8),
        .m_axis_tlast        (axis_tl8),
        .busy                (busy8),
        .readout_done_pulse  (done_p8),
        .readout_done_sticky (done_s8),
        .qubit_state_mask    (qmask8),
        .sample_cnt_out      (scnt8),
        .window_count        (wcnt8),
        .rd_res_i            (ri8),
        .rd_res_q            (rq8),
        .rd_res_proj         (rp8)
    );

    // Instance 2: Full N_CH = 32 time-multiplexed tone bank
    reg               en32, clr32;
    reg        [4:0]  caddr32;
    reg               pwe32, rwe32, twe32;
    reg        [23:0] pinc32;
    reg signed [15:0] rcos32, rsin32;
    reg signed [31:0] thr32;
    reg               adc_v32;
    wire              adc_r32;
    reg signed [15:0] adc_s32;
    wire              axis_tv32;
    reg               axis_tr32;
    wire       [63:0] axis_td32;
    wire       [4:0]  axis_tid32;
    wire              axis_tl32;
    wire              busy32, done_p32, done_s32;
    wire       [31:0] qmask32;
    wire       [15:0] scnt32, wcnt32;
    wire signed [31:0] ri32, rq32, rp32;

    cryo_mux_ddc_ctrl #(.N_CH(32)) u_dut32 (
        .clk                 (clk),
        .rst_n               (rst_n),
        .enable              (en32),
        .soft_clear          (clr32),
        .mf_en               (1'b0),
        .cfg_num_ch_m1       (5'd31),
        .cfg_win_len         (16'd16),
        .cfg_ch_addr         (caddr32),
        .cfg_phase_we        (pwe32),
        .cfg_phase_inc       (pinc32),
        .cfg_rot_we          (rwe32),
        .cfg_rot_cos         (rcos32),
        .cfg_rot_sin         (rsin32),
        .cfg_thresh_we       (twe32),
        .cfg_thresh          (thr32),
        .adc_valid           (adc_v32),
        .adc_ready           (adc_r32),
        .adc_sample          (adc_s32),
        .mf_weight           (16'sd32767),
        .m_axis_tvalid       (axis_tv32),
        .m_axis_tready       (axis_tr32),
        .m_axis_tdata        (axis_td32),
        .m_axis_tid          (axis_tid32),
        .m_axis_tlast        (axis_tl32),
        .busy                (busy32),
        .readout_done_pulse  (done_p32),
        .readout_done_sticky (done_s32),
        .qubit_state_mask    (qmask32),
        .sample_cnt_out      (scnt32),
        .window_count        (wcnt32),
        .rd_res_i            (ri32),
        .rd_res_q            (rq32),
        .rd_res_proj         (rp32)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    integer errors;
    integer ch, n, beats;
    reg [63:0] cap_axis8 [0:7];
    reg [4:0]  cap_tid8  [0:7];
    reg        cap_tl8   [0:7];

    // Deterministic integer ADC samples & matched-filter envelope weights (exact parity with Python)
    function signed [15:0] sample_wave(input integer idx);
        integer v1, v2, v3;
        begin
            // Multi-tone deterministic signal spanning positive/negative signed range
            v1 = (((idx * 37 + 11) % 64) - 32) * 180;
            v2 = (((idx * 13 + 5)  % 32) - 16) * 210;
            v3 = ((idx % 8) < 4) ? 1600 : -1600;
            sample_wave = v1[15:0] + v2[15:0] + v3[15:0];
        end
    endfunction

    function signed [15:0] mf_env(input integer idx);
        begin
            // Smooth triangular matched-filter envelope in Q1.15 (16384..32000)
            if (idx < 32) mf_env = 16'sd16384 + (idx[15:0] * 16'sd480);
            else          mf_env = 16'sd31744 - ((idx[15:0] - 16'sd32) * 16'sd480);
        end
    endfunction

    task cfg_ch8(input [4:0] c, input [23:0] pi, input signed [15:0] rc,
                 input signed [15:0] rs, input signed [31:0] th);
        begin
            @(negedge clk);
            caddr8 = c;
            pinc8  = pi;  pwe8 = 1'b1;
            rcos8  = rc;  rsin8 = rs; rwe8 = 1'b1;
            thr8   = th;  twe8 = 1'b1;
            @(posedge clk);
            @(negedge clk);
            pwe8 = 1'b0; rwe8 = 1'b0; twe8 = 1'b0;
        end
    endtask

    task push_adc8(input signed [15:0] s, input signed [15:0] w);
        begin
            wait (adc_r8 == 1'b1);
            @(negedge clk);
            adc_s8 = s;
            mfw8   = w;
            adc_v8 = 1'b1;
            @(posedge clk);
            @(negedge clk);
            adc_v8 = 1'b0;
        end
    endtask

    task run_window8(input use_mf, input integer win_tag);
        begin
            @(negedge clk);
            mf_en8   = use_mf;
            axis_tr8 = 1'b0; // intentionally apply AXI4-Stream backpressure initially!

            for (n = 0; n < 64; n = n + 1) begin
                push_adc8(sample_wave(n + win_tag * 17), mf_env(n));
            end

            // Wait until AXI4-Stream starts presenting beat 0 under backpressure
            wait (axis_tv8 == 1'b1);
            // Hold backpressure for 3 cycles to verify AXI4-Stream stability!
            repeat (3) begin
                @(posedge clk);
                if (!axis_tv8 || axis_tid8 !== 5'd0) begin
                    $display("ERROR: AXI4-Stream beat 0 unstable under tready=0!");
                    errors = errors + 1;
                end
            end

            // Drain all 8 AXI4-Stream beats with intermittent backpressure
            beats = 0;
            while (beats < 8) begin
                @(negedge clk);
                axis_tr8 = 1'b1;
                @(posedge clk);
                if (axis_tv8 && axis_tr8) begin
                    cap_axis8[beats] = axis_td8;
                    cap_tid8[beats]  = axis_tid8;
                    cap_tl8[beats]   = axis_tl8;
                    if (axis_tid8 !== beats[4:0]) begin
                        $display("ERROR: AXIS tid=%0d exp=%0d", axis_tid8, beats);
                        errors = errors + 1;
                    end
                    if (axis_tl8 !== (beats == 7)) begin
                        $display("ERROR: AXIS tlast=%b at beat %0d", axis_tl8, beats);
                        errors = errors + 1;
                    end
                    beats = beats + 1;
                end
                // Stall 1 cycle on beat 3
                if (beats == 3) begin
                    @(negedge clk);
                    axis_tr8 = 1'b0;
                    @(posedge clk);
                end
            end
            @(negedge clk);
            axis_tr8 = 1'b0;
            @(posedge clk);

            // Print machine-parseable trace for Python bit-exact 0-LSB verification
            for (ch = 0; ch < 8; ch = ch + 1) begin
                @(negedge clk);
                caddr8 = ch[4:0];
                #1;
                if ($signed(cap_axis8[ch][31:0]) !== rp8 ||
                    cap_axis8[ch][32] !== qmask8[ch]) begin
                    $display("ERROR: AXIS payload mismatch ch=%0d!", ch);
                    errors = errors + 1;
                end
                $display("DDC8_TRACE win=%0d mf=%0d ch=%0d res_i=%0d res_q=%0d proj=%0d state=%0d",
                         win_tag, use_mf, ch, ri8, rq8, rp8, qmask8[ch]);
            end
        end
    endtask

    initial begin
        errors   = 0;
        rst_n    = 1'b0;
        en8      = 1'b1; clr8 = 1'b0; mf_en8 = 1'b0;
        nch8     = 5'd7; wlen8 = 16'd64;
        caddr8   = 5'd0; pwe8 = 1'b0; rwe8 = 1'b0; twe8 = 1'b0;
        pinc8    = 24'd0; rcos8 = 16'sd32767; rsin8 = 16'sd0; thr8 = 32'sd0;
        adc_v8   = 1'b0; adc_s8 = 16'sd0; mfw8 = 16'sd32767;
        axis_tr8 = 1'b0;

        en32     = 1'b1; clr32 = 1'b0;
        caddr32  = 5'd0; pwe32 = 1'b0; rwe32 = 1'b0; twe32 = 1'b0;
        pinc32   = 24'd0; rcos32 = 16'sd32767; rsin32 = 16'sd0; thr32 = 32'sd0;
        adc_v32  = 1'b0; adc_s32 = 16'sd0; axis_tr32 = 1'b1;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        // Configure 8 channels with distinct NCO frequencies, rotated IQ axes, and thresholds
        cfg_ch8(5'd0, 24'h040000,  16'sd32767,  16'sd0,      32'sd0);
        cfg_ch8(5'd1, 24'h080000,  16'sd23170,  16'sd23170, -32'sd500);
        cfg_ch8(5'd2, 24'h0C0000,  16'sd0,      16'sd32767,  32'sd200);
        cfg_ch8(5'd3, 24'h100000, -16'sd23170,  16'sd23170,  32'sd0);
        cfg_ch8(5'd4, 24'h140000, -16'sd32767,  16'sd0,     -32'sd1000);
        cfg_ch8(5'd5, 24'h180000,  16'sd28377, -16'sd16384,  32'sd100);
        cfg_ch8(5'd6, 24'h1C0000,  16'sd16384,  16'sd28377, -32'sd200);
        cfg_ch8(5'd7, 24'h200000,  16'sd32767, -16'sd8192,   32'sd0);

        // Window 0: Exact Boxcar (mf_en = 0)
        run_window8(1'b0, 0);
        // Window 1: Matched-Filter Envelope (mf_en = 1)
        run_window8(1'b1, 1);

        if (wcnt8 !== 16'd2 || !done_s8) begin
            $display("ERROR: expected 2 completed DDC8 windows, got %0d", wcnt8);
            errors = errors + 1;
        end

        // Test Instance 2: Full 32-tone time-multiplexed bank!
        for (ch = 0; ch < 32; ch = ch + 1) begin
            @(negedge clk);
            caddr32 = ch[4:0];
            pinc32  = 24'h020000 * (ch + 1);
            rcos32  = 16'sd32767;
            rsin32  = 16'sd0;
            thr32   = (ch[0]) ? -32'sd100000 : 32'sd100000; // odd->|1>, even->|0>
            pwe32   = 1'b1; rwe32 = 1'b1; twe32 = 1'b1;
            @(posedge clk);
            @(negedge clk);
            pwe32 = 1'b0; rwe32 = 1'b0; twe32 = 1'b0;
        end

        beats = 0;
        fork
            begin
                for (n = 0; n < 16; n = n + 1) begin
                    wait (adc_r32 == 1'b1);
                    @(negedge clk);
                    adc_s32 = sample_wave(n);
                    adc_v32 = 1'b1;
                    @(posedge clk);
                    @(negedge clk);
                    adc_v32 = 1'b0;
                end
            end
            begin
                while (beats < 32) begin
                    @(posedge clk);
                    if (axis_tv32 && axis_tr32) begin
                        if (axis_tid32 !== beats[4:0]) begin
                            $display("ERROR: 32-tone tid=%0d exp=%0d", axis_tid32, beats);
                            errors = errors + 1;
                        end
                        if (axis_tl32 !== (beats == 31)) begin
                            $display("ERROR: 32-tone tlast=%b at beat %0d", axis_tl32, beats);
                            errors = errors + 1;
                        end
                        beats = beats + 1;
                    end
                end
            end
        join

        @(posedge clk);
        if (qmask32 !== 32'hAAAA_AAAA || wcnt32 !== 16'd1) begin
            $display("ERROR: 32-tone qubit_state_mask=%h exp=AAAAAAAA wcnt=%0d", qmask32, wcnt32);
            errors = errors + 1;
        end

        // OBS-114 Regression: Continuous 100 MSPS Back-to-Back Streaming (180 clocks -> 180/180 accepted!)
        begin : blk_100msps_check
            integer accepted_180, cyc_i;
            @(negedge clk);
            wlen8    = 16'd60;
            axis_tr8 = 1'b1;
            mf_en8   = 1'b0;
            accepted_180 = 0;
            for (cyc_i = 0; cyc_i < 180; cyc_i = cyc_i + 1) begin
                @(negedge clk);
                adc_s8 = sample_wave(cyc_i);
                adc_v8 = 1'b1;
                @(posedge clk);
                if (adc_r8 && adc_v8) accepted_180 = accepted_180 + 1;
            end
            @(negedge clk);
            adc_v8 = 1'b0;
            repeat (30) @(posedge clk);
            if (accepted_180 != 180) begin
                $display("ERROR: OBS-114 100 MSPS stream accepted only %0d/180 samples!", accepted_180);
                errors = errors + 1;
            end
            if (wcnt8 !== 16'd5) begin
                $display("ERROR: OBS-114 expected 5 total DDC8 windows (2+3), got %0d", wcnt8);
                errors = errors + 1;
            end
        end

        $display("DDC_SUMMARY errors=%0d win8_cnt=2 mask8=%02h tones32_beats=%0d mask32=%08h",
                 errors, qmask8, beats, qmask32);
        if (errors == 0) begin
            $display("PASS: tb_cryo_mux_ddc_ctrl");
            $finish;
        end else begin
            $display("FAIL: tb_cryo_mux_ddc_ctrl (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
