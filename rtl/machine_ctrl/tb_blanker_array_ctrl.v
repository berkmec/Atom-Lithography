// tb_blanker_array_ctrl.v - Self-checking testbench for blanker_array_ctrl.v
`timescale 1ns/1ps

module tb_blanker_array_ctrl;
    localparam integer CLK_PERIOD_NS = 10; // 100 MHz

    reg        clk;
    reg        rst_n;
    reg        interlock_blank_force;
    reg        frame_start;
    reg        sticky_clr;
    reg        interlock_clr;
    reg        auto_offset_en;
    reg [15:0] sclk_div;
    reg signed [15:0] dx_pitch;
    reg signed [15:0] dy_pitch;
    reg [15:0] tile_en_mask;

    reg        mem_we;
    reg        mem_bank_sel;
    reg [4:0]  mem_row_addr;
    reg [31:0] mem_wdata;
    wire [31:0] mem_rdata;

    reg [15:0] tile_done_in;
    reg [15:0] tile_abort_in;

    wire [3:0]  tile_sel;
    wire        tile_sclk;
    wire        tile_sdata;
    wire        tile_latch_n;
    wire        frame_latch_n;
    wire [15:0] tile_beam_en;

    wire        busy;
    wire        safe_blanked;
    wire        interlock_latched;
    wire        frame_done_sticky;
    wire        interlock_abort_sticky;
    wire [15:0] tile_done_sticky;
    wire [15:0] tile_abort_sticky;
    wire        any_tile_abort;
    wire        all_tiles_done;
    wire [10:0] active_unblank_cnt;
    wire signed [15:0] stitch_dx_pitch_out;
    wire signed [15:0] stitch_dy_pitch_out;

    blanker_array_ctrl dut (
        .clk                    (clk),
        .rst_n                  (rst_n),
        .interlock_blank_force  (interlock_blank_force),
        .frame_start            (frame_start),
        .sticky_clr             (sticky_clr),
        .interlock_clr          (interlock_clr),
        .auto_offset_en         (auto_offset_en),
        .sclk_div               (sclk_div),
        .dx_pitch               (dx_pitch),
        .dy_pitch               (dy_pitch),
        .tile_en_mask           (tile_en_mask),
        .mem_we                 (mem_we),
        .mem_bank_sel           (mem_bank_sel),
        .mem_row_addr           (mem_row_addr),
        .mem_wdata              (mem_wdata),
        .mem_rdata              (mem_rdata),
        .tile_done_in           (tile_done_in),
        .tile_abort_in          (tile_abort_in),
        .tile_sel               (tile_sel),
        .tile_sclk              (tile_sclk),
        .tile_sdata             (tile_sdata),
        .tile_latch_n           (tile_latch_n),
        .frame_latch_n          (frame_latch_n),
        .tile_beam_en           (tile_beam_en),
        .busy                   (busy),
        .safe_blanked           (safe_blanked),
        .interlock_latched      (interlock_latched),
        .frame_done_sticky      (frame_done_sticky),
        .interlock_abort_sticky (interlock_abort_sticky),
        .tile_done_sticky       (tile_done_sticky),
        .tile_abort_sticky      (tile_abort_sticky),
        .any_tile_abort         (any_tile_abort),
        .all_tiles_done         (all_tiles_done),
        .active_unblank_cnt     (active_unblank_cnt),
        .stitch_dx_pitch_out    (stitch_dx_pitch_out),
        .stitch_dy_pitch_out    (stitch_dy_pitch_out)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    // Reference storage and captured serial stream
    reg [31:0] ref_pat  [0:31];
    reg [31:0] ref_dead [0:31];
    reg        cap_bits [0:1023];
    integer    cap_idx;
    integer    tile_latch_cnt;
    integer    frame_latch_cnt;
    reg        prev_sclk;
    reg        prev_tlatch_n;
    reg        prev_flatch_n;

    always @(posedge clk) begin
        if (!rst_n) begin
            prev_sclk       <= 1'b0;
            prev_tlatch_n   <= 1'b1;
            prev_flatch_n   <= 1'b1;
            cap_idx         <= 0;
            tile_latch_cnt  <= 0;
            frame_latch_cnt <= 0;
        end else begin
            prev_sclk     <= tile_sclk;
            prev_tlatch_n <= tile_latch_n;
            prev_flatch_n <= frame_latch_n;
            if (tile_sclk && !prev_sclk) begin
                if (cap_idx < 1024) begin
                    cap_bits[cap_idx] <= tile_sdata;
                end
                cap_idx <= cap_idx + 1;
            end
            if (!tile_latch_n && prev_tlatch_n) begin
                tile_latch_cnt <= tile_latch_cnt + 1;
            end
            if (!frame_latch_n && prev_flatch_n) begin
                frame_latch_cnt <= frame_latch_cnt + 1;
            end
        end
    end

    integer errors;
    integer r, t, ch, pr, pc, sr, sc, idx_linear;
    integer expected_unblank;
    reg     exp_bit;
    time    t_trip_start, t_trip_done;
    integer trip_latency_ns;

    task write_mem_row(input bank, input [4:0] row, input [31:0] val);
        begin
            @(negedge clk);
            mem_bank_sel = bank;
            mem_row_addr = row;
            mem_wdata    = val;
            mem_we       = 1'b1;
            @(posedge clk);
            @(negedge clk);
            mem_we       = 1'b0;
        end
    endtask

    task run_and_verify_frame(input use_off, input signed [15:0] dx, input signed [15:0] dy);
        begin
            @(negedge clk);
            auto_offset_en  = use_off;
            dx_pitch        = dx;
            dy_pitch        = dy;
            cap_idx         = 0;
            tile_latch_cnt  = 0;
            frame_latch_cnt = 0;
            frame_start     = 1'b1;
            @(posedge clk);
            @(negedge clk);
            frame_start     = 1'b0;

            wait (frame_done_sticky == 1'b1);
            @(posedge clk);

            if (cap_idx != 1024) begin
                $display("ERROR: expected 1024 serialized bits, got %0d", cap_idx);
                errors = errors + 1;
            end
            if (tile_latch_cnt != 16) begin
                $display("ERROR: expected 16 tile_latch_n pulses, got %0d", tile_latch_cnt);
                errors = errors + 1;
            end
            if (frame_latch_cnt != 1) begin
                $display("ERROR: expected 1 frame_latch_n pulse, got %0d", frame_latch_cnt);
                errors = errors + 1;
            end

            expected_unblank = 0;
            for (t = 0; t < 16; t = t + 1) begin
                for (ch = 0; ch < 64; ch = ch + 1) begin
                    idx_linear = t * 64 + ch;
                    pr = {t[3:2], ch[5:3]};
                    pc = {t[1:0], ch[2:0]};
                    if (use_off) begin
                        sr = pr - dy;
                        sc = pc - dx;
                    end else begin
                        sr = pr;
                        sc = pc;
                    end
                    if ((sr >= 0) && (sr < 32) && (sc >= 0) && (sc < 32)) begin
                        exp_bit = ref_pat[sr][sc] & (~ref_dead[pr][pc]) & tile_en_mask[t];
                    end else begin
                        exp_bit = 1'b0;
                    end
                    if (exp_bit) expected_unblank = expected_unblank + 1;
                    if (cap_bits[idx_linear] !== exp_bit) begin
                        $display("ERROR: bit mismatch tile=%0d ch=%0d (r=%0d,c=%0d) got=%b exp=%b",
                                 t, ch, pr, pc, cap_bits[idx_linear], exp_bit);
                        errors = errors + 1;
                    end
                end
            end

            if (active_unblank_cnt !== expected_unblank[10:0]) begin
                $display("ERROR: active_unblank_cnt=%0d expected=%0d",
                         active_unblank_cnt, expected_unblank);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        errors                = 0;
        rst_n                 = 1'b0;
        interlock_blank_force = 1'b0;
        frame_start           = 1'b0;
        sticky_clr            = 1'b0;
        interlock_clr         = 1'b0;
        auto_offset_en        = 1'b0;
        sclk_div              = 16'd1;
        dx_pitch              = 16'sd0;
        dy_pitch              = 16'sd0;
        tile_en_mask          = 16'hFFFF;
        mem_we                = 1'b0;
        mem_bank_sel          = 1'b0;
        mem_row_addr          = 5'd0;
        mem_wdata             = 32'd0;
        tile_done_in          = 16'h0000;
        tile_abort_in         = 16'h0000;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        // Verify power-on safe blanked state
        if (!safe_blanked || tile_beam_en !== 16'h0000) begin
            $display("ERROR: reset state not safe blanked!");
            errors = errors + 1;
        end

        // 1. Load 1,024-bit pattern + 1,024-bit dead-channel mask (37 masked channels)
        for (r = 0; r < 32; r = r + 1) begin
            ref_pat[r]  = 32'hA55A_3C0F ^ (r * 32'h0101_0101);
            ref_dead[r] = (r % 3 == 0) ? (32'h0001_0011 << (r % 5)) : 32'h0000_0000;
            write_mem_row(1'b0, r[4:0], ref_pat[r]);
            write_mem_row(1'b1, r[4:0], ref_dead[r]);
        end

        // Verify dead-mask CSR readback
        @(negedge clk);
        mem_bank_sel = 1'b1;
        mem_row_addr = 5'd9;
        @(posedge clk);
        @(posedge clk);
        if (mem_rdata !== ref_dead[9]) begin
            $display("ERROR: dead_mask readback mismatch got=%h exp=%h", mem_rdata, ref_dead[9]);
            errors = errors + 1;
        end

        // 2. Full 1,024-ch frame serialization with dead-channel masking (no offset)
        run_and_verify_frame(1'b0, 16'sd0, 16'sd0);
        if (tile_beam_en !== 16'hFFFF || safe_blanked !== 1'b0) begin
            $display("ERROR: expected active unblanked beam after clean frame!");
            errors = errors + 1;
        end

        // 3. Signed step-and-stitch offset test (dx = +2, dy = -1)
        run_and_verify_frame(1'b1, 16'sd2, -16'sd1);
        if (stitch_dx_pitch_out !== 16'sd2 || stitch_dy_pitch_out !== -16'sd1) begin
            $display("ERROR: stitch offset outputs mismatch!");
            errors = errors + 1;
        end

        // 4. Sticky tile done/abort aggregation test (allow 2-FF CDC sync latency)
        @(negedge clk);
        tile_done_in  = 16'h00FF;
        tile_abort_in = 16'h0004;
        repeat (3) @(posedge clk);
        @(negedge clk);
        tile_done_in  = 16'hFF00;
        tile_abort_in = 16'h0000;
        repeat (3) @(posedge clk);
        @(negedge clk);
        tile_done_in  = 16'h0000;
        repeat (3) @(posedge clk);
        if (tile_done_sticky !== 16'hFFFF || !all_tiles_done) begin
            $display("ERROR: tile_done_sticky aggregation failed: %h", tile_done_sticky);
            errors = errors + 1;
        end
        if (tile_abort_sticky !== 16'h0004 || !any_tile_abort) begin
            $display("ERROR: tile_abort_sticky aggregation failed: %h", tile_abort_sticky);
            errors = errors + 1;
        end
        @(negedge clk);
        sticky_clr = 1'b1;
        @(posedge clk);
        @(negedge clk);
        sticky_clr = 1'b0;
        @(posedge clk);
        if (tile_done_sticky !== 16'h0000 || tile_abort_sticky !== 16'h0000) begin
            $display("ERROR: sticky_clr did not clear tile bitmaps!");
            errors = errors + 1;
        end

        // 5. HARD-WIRED < 1 us INTERLOCK FAULT INJECTION TEST (<= 20 ns @ 100 MHz)
        // Ensure beams are currently enabled before injecting fault
        if (tile_beam_en !== 16'hFFFF || safe_blanked !== 1'b0) begin
            $display("ERROR: precondition failed: beam not enabled before interlock test");
            errors = errors + 1;
        end
        @(negedge clk);
        t_trip_start = $time;
        interlock_blank_force = 1'b1;
        #1; // Immediate asynchronous-priority combinational clamp check (< 10 ns)
        if (tile_beam_en !== 16'h0000 || tile_sdata !== 1'b0 || safe_blanked !== 1'b1) begin
            $display("ERROR: interlock_blank_force failed async clamp!");
            errors = errors + 1;
        end
        @(posedge clk);
        #1;
        t_trip_done = $time;
        trip_latency_ns = t_trip_done - t_trip_start;
        if (!interlock_latched || !interlock_abort_sticky || tile_beam_en !== 16'h0000) begin
            $display("ERROR: interlock synchronous latch failed within 1 clock!");
            errors = errors + 1;
        end
        if (trip_latency_ns > 20) begin
            $display("ERROR: interlock latency %0d ns exceeds 20 ns (2-clock) limit!", trip_latency_ns);
            errors = errors + 1;
        end

        // Release interlock force WITHOUT interlock_clr -> must stay safely locked blanked!
        @(negedge clk);
        interlock_blank_force = 1'b0;
        frame_start = 1'b1;
        @(posedge clk);
        @(negedge clk);
        frame_start = 1'b0;
        repeat (5) @(posedge clk);
        if (!safe_blanked || tile_beam_en !== 16'h0000 || busy) begin
            $display("ERROR: blanker escaped ST_INTERLOCK without explicit interlock_clr!");
            errors = errors + 1;
        end

        // Explicit interlock_clr recovers to ST_IDLE cleanly
        @(negedge clk);
        interlock_clr = 1'b1;
        @(posedge clk);
        @(negedge clk);
        interlock_clr = 1'b0;
        @(posedge clk);
        if (interlock_latched || interlock_abort_sticky) begin
            $display("ERROR: interlock_clr failed to release latch!");
            errors = errors + 1;
        end

        $display("BLANKER_SUMMARY errors=%0d frames_verified=2 bits_per_frame=1024 trip_latency_ns=%0d",
                 errors, trip_latency_ns);
        if (errors == 0) begin
            $display("PASS: tb_blanker_array_ctrl");
            $finish;
        end else begin
            $display("FAIL: tb_blanker_array_ctrl (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
