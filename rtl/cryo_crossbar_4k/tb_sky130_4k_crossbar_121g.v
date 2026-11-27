// tb_sky130_4k_crossbar_121g.v - Self-Checking 8-Die 968-Gate Daisy-Chain Crossbar Testbench
// Verifies:
//   1. Power-on fail-safe clamped state across all 8 dies (0/968 gates active)
//   2. Full 8-die x 16-bit = 128-bit SPI daisy-chain programming addressing all 968 gates (8 x 121)
//   3. Exact 11x11 (row_sel, col_sel) & strict 1-hot mutual exclusion (popcount <= 1 per die)
//   4. Out-of-bounds address (121..127) safe rejection + fault_oob_addr flag
//   5. Cyclic 121-gate refresh scan visiting every gate 0..120 in sequence
//   6. OP_ALL_SAFE_ZERO emergency disconnect across all 968 gates
`timescale 1ns/1ps

module tb_sky130_4k_crossbar_121g;
    localparam integer N_DIES  = 8;
    localparam integer N_GATES = 121;
    localparam integer TOTAL_G = N_DIES * N_GATES; // 968 gates

    reg        clk;
    reg        rst_n;
    reg        spi_clk;
    reg        spi_cs_n;
    reg        spi_mosi;
    wire [N_DIES:0] spi_chain;
    assign spi_chain[0] = spi_mosi;

    wire [10:0]  die_row_sel   [0:N_DIES-1];
    wire [10:0]  die_col_sel   [0:N_DIES-1];
    wire [120:0] die_gate_sel  [0:N_DIES-1];
    wire [6:0]   die_addr      [0:N_DIES-1];
    wire [3:0]   die_tag       [0:N_DIES-1];
    wire [N_DIES-1:0] die_valid;
    wire [N_DIES-1:0] die_refresh;
    wire [N_DIES-1:0] die_clamped;
    wire [N_DIES-1:0] die_oob;

    genvar m;
    generate
        for (m = 0; m < N_DIES; m = m + 1) begin : g_die
            sky130_4k_crossbar_121g u_die (
                .clk              (clk),
                .rst_n            (rst_n),
                .spi_clk          (spi_clk),
                .spi_cs_n         (spi_cs_n),
                .spi_din          (spi_chain[m]),
                .spi_dout         (spi_chain[m + 1]),
                .row_sel          (die_row_sel[m]),
                .col_sel          (die_col_sel[m]),
                .gate_sel         (die_gate_sel[m]),
                .active_gate_addr (die_addr[m]),
                .dac_bus_tag      (die_tag[m]),
                .gate_valid       (die_valid[m]),
                .refresh_en       (die_refresh[m]),
                .safe_clamped     (die_clamped[m]),
                .fault_oob_addr   (die_oob[m])
            );
        end
    endgenerate

    initial clk = 1'b0;
    always #5 clk = ~clk;

    integer errors;
    integer d, g_i, b_i, ones, r_exp, c_exp;
    reg [15:0] cmd_words [0:N_DIES-1];
    reg [120:0] visited_mask;

    // Shift 8 x 16-bit commands across daisy-chain M0 -> M1 -> ... -> M7
    // (shift M7 first so it arrives at M7, M0 last so it lands in M0!)
    task send_chain_8x16;
        integer di, bi;
        reg [15:0] w;
        begin
            @(negedge clk);
            spi_cs_n = 1'b0;
            spi_clk  = 1'b0;
            repeat (2) @(posedge clk);
            for (di = N_DIES - 1; di >= 0; di = di - 1) begin
                w = cmd_words[di];
                for (bi = 15; bi >= 0; bi = bi - 1) begin
                    @(negedge clk);
                    spi_mosi = w[bi];
                    spi_clk  = 1'b0;
                    repeat (2) @(posedge clk);
                    @(negedge clk);
                    spi_clk  = 1'b1;
                    repeat (2) @(posedge clk);
                end
            end
            @(negedge clk);
            spi_clk  = 1'b0;
            repeat (2) @(posedge clk);
            @(negedge clk);
            spi_cs_n = 1'b1;
            repeat (5) @(posedge clk);
        end
    endtask

    function integer popcount121(input [120:0] vec);
        integer k, cnt;
        begin
            cnt = 0;
            for (k = 0; k < 121; k = k + 1) begin
                if (vec[k]) cnt = cnt + 1;
            end
            popcount121 = cnt;
        end
    endfunction

    initial begin
        errors   = 0;
        rst_n    = 1'b0;
        spi_clk  = 1'b0;
        spi_cs_n = 1'b1;
        spi_mosi = 1'b0;
        for (d = 0; d < N_DIES; d = d + 1) cmd_words[d] = 16'd0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);
        #1;

        // 1. Verify power-on fail-safe clamp across all 8 dies (0/968 active)
        if (die_clamped !== 8'hFF || die_valid !== 8'h00) begin
            $display("ERROR: boot safe clamp failed clamped=%h valid=%h", die_clamped, die_valid);
            errors = errors + 1;
        end
        for (d = 0; d < N_DIES; d = d + 1) begin
            if (die_gate_sel[d] !== 121'd0) begin
                $display("ERROR: die %0d non-zero gate_sel on boot!", d);
                errors = errors + 1;
            end
        end

        // 2. Sweep ALL 121 gate addresses across ALL 8 daisy-chained dies simultaneously (968 gates!)
        for (g_i = 0; g_i < N_GATES; g_i = g_i + 1) begin
            for (d = 0; d < N_DIES; d = d + 1) begin
                // Distinct per-die offset modulo 121 so every die decodes a different gate simultaneously
                b_i = (g_i + d * 13) % 121;
                cmd_words[d] = {2'b01, 3'b000, b_i[6:0], d[3:0]};
            end
            send_chain_8x16();
            #1;
            for (d = 0; d < N_DIES; d = d + 1) begin
                b_i   = (g_i + d * 13) % 121;
                r_exp = b_i / 11;
                c_exp = b_i % 11;
                ones  = popcount121(die_gate_sel[d]);
                if (!die_valid[d] || ones != 1 || !die_gate_sel[d][b_i] ||
                    die_row_sel[d] !== (11'd1 << r_exp) || die_col_sel[d] !== (11'd1 << c_exp) ||
                    die_addr[d] !== b_i[6:0] || die_tag[d] !== d[3:0] || die_oob[d]) begin
                    $display("ERROR: die=%0d gate=%0d (r=%0d,c=%0d) ones=%0d row=%b col=%b oob=%b",
                             d, b_i, r_exp, c_exp, ones, die_row_sel[d], die_col_sel[d], die_oob[d]);
                    errors = errors + 1;
                end
            end
        end

        // 3. Test OOB address (121..127) rejection on die 3 while others hold valid gate 0
        for (d = 0; d < N_DIES; d = d + 1) begin
            cmd_words[d] = (d == 3) ? {2'b01, 3'b000, 7'd125, 4'h3} : {2'b01, 3'b000, 7'd0, d[3:0]};
        end
        send_chain_8x16();
        #1;
        if (!die_oob[3] || !die_clamped[3] || die_valid[3] || die_gate_sel[3] !== 121'd0) begin
            $display("ERROR: OOB addr 125 on die 3 was not safely clamped!");
            errors = errors + 1;
        end

        // 4. Test cyclic 121-gate S&H refresh scan on die 0 (dwell=1)
        for (d = 0; d < N_DIES; d = d + 1) begin
            cmd_words[d] = {2'b10, 3'b000, 7'd1, 4'b0001}; // refresh_en=1, dwell=1
        end
        send_chain_8x16();
        visited_mask = 121'd0;
        for (g_i = 0; g_i < 130; g_i = g_i + 1) begin
            @(posedge clk);
            #1;
            if (die_valid[0]) visited_mask = visited_mask | die_gate_sel[0];
        end
        if (popcount121(visited_mask) != 121) begin
            $display("ERROR: refresh scan visited only %0d/121 gates!", popcount121(visited_mask));
            errors = errors + 1;
        end

        // 5. Test OP_ALL_SAFE_ZERO across all 8 dies (968 gates disconnected!)
        for (d = 0; d < N_DIES; d = d + 1) begin
            cmd_words[d] = {2'b11, 14'd0};
        end
        send_chain_8x16();
        #1;
        if (die_clamped !== 8'hFF || die_valid !== 8'h00) begin
            $display("ERROR: OP_ALL_SAFE_ZERO failed clamped=%h valid=%h", die_clamped, die_valid);
            errors = errors + 1;
        end

        $display("CROSSBAR_4K_SUMMARY errors=%0d dies=%0d gates_per_die=%0d total_gates=%0d trl=2_pending_4k_pdk",
                 errors, N_DIES, N_GATES, TOTAL_G);
        if (errors == 0) begin
            $display("PASS: tb_sky130_4k_crossbar_121g");
            $finish;
        end else begin
            $display("FAIL: tb_sky130_4k_crossbar_121g (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
