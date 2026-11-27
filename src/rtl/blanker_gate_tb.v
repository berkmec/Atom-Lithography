// Self-checking testbench for blanker_gate (run with iverilog -g2012 -Wall + vvp).
// Verifies:
//   CASE 1: Single counted ion with 30 ns (3-clock @ 100 MHz) IBIC pulse -> counts ONCE!
//   CASE 2: No detector hit -> watchdog timeout_abort fires and closes blanker.
//   CASE 3: target_count == 3 requires 3 distinct IBIC pulses (multi-cycle pulses count once each).
//   CASE 4: target_count == 0 NEVER opens blanker (safe zero-target rejection).
`timescale 1ns/1ps
module blanker_gate_tb;
    reg clk = 0;
    reg rst_n = 0;
    reg start = 0;
    reg count_hit = 0;
    reg [7:0] target_count = 8'd1;

    wire blanker_open, busy, done, timeout_abort;
    wire [7:0] counted;
    integer errors = 0;
    integer t;
    integer done_seen;
    integer abort_seen;

    blanker_gate #(.WATCHDOG_CYCLES(50)) dut (
        .clk           (clk),
        .rst_n         (rst_n),
        .start         (start),
        .target_count  (target_count),
        .count_hit     (count_hit),
        .blanker_open  (blanker_open),
        .busy          (busy),
        .done          (done),
        .timeout_abort (timeout_abort),
        .counted       (counted)
    );

    always #5 clk = ~clk;

    task check(input cond, input [255:0] msg);
        if (!cond) begin
            errors = errors + 1;
            $display("FAIL: %0s t=%0t", msg, $time);
        end
    endtask

    // Drive a 30 ns (3-clock @ 100 MHz) IBIC pulse cleanly on negedge clk
    task drive_ibic_pulse_30ns;
        begin
            @(negedge clk);
            count_hit = 1'b1;
            repeat (3) @(posedge clk);
            @(negedge clk);
            count_hit = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        // Wait for 2-FF reset synchronizer release
        repeat (4) @(posedge clk);
        #1;
        check(blanker_open === 1'b0 && busy === 1'b0, "blanker closed after reset");

        // CASE 1: target_count=1 with 30 ns (3-clock) IBIC pulse -> counted==1 (NOT 3!) & done pulses once
        @(negedge clk);
        target_count = 8'd1;
        start        = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start        = 1'b0;
        #1;
        check(busy === 1'b1 && blanker_open === 1'b1, "case1 busy and open in RUN");

        done_seen = 0;
        @(negedge clk);
        count_hit = 1'b1;
        for (t = 0; t < 3; t = t + 1) begin
            @(posedge clk);
            #1;
            if (done) done_seen = done_seen + 1;
        end
        @(negedge clk);
        count_hit = 1'b0;
        for (t = 0; t < 4; t = t + 1) begin
            @(posedge clk);
            #1;
            if (done) done_seen = done_seen + 1;
        end
        check(done_seen == 1, "case1 done pulses exactly once");
        check(counted === 8'd1, "case1 30ns pulse counted exactly once");
        check(blanker_open === 1'b0 && busy === 1'b0, "case1 idle after done");

        // CASE 2: no detector hit -> watchdog timeout_abort fires exactly once
        @(negedge clk);
        target_count = 8'd1;
        start        = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start        = 1'b0;
        abort_seen   = 0;
        for (t = 0; t < 65; t = t + 1) begin
            @(posedge clk);
            #1;
            if (timeout_abort) abort_seen = abort_seen + 1;
        end
        check(abort_seen == 1, "case2 watchdog timeout_abort fires once");
        check(blanker_open === 1'b0 && busy === 1'b0, "case2 blanker closed after abort");

        // CASE 3: target_count=3 requires three distinct 30 ns IBIC pulses
        @(negedge clk);
        target_count = 8'd3;
        start        = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start        = 1'b0;
        drive_ibic_pulse_30ns();
        #1;
        check(busy === 1'b1 && counted === 8'd1, "case3 pulse 1 -> counted==1");
        drive_ibic_pulse_30ns();
        #1;
        check(busy === 1'b1 && counted === 8'd2, "case3 pulse 2 -> counted==2");
        done_seen = 0;
        @(negedge clk);
        count_hit = 1'b1;
        for (t = 0; t < 3; t = t + 1) begin
            @(posedge clk);
            #1;
            if (done) done_seen = done_seen + 1;
        end
        @(negedge clk);
        count_hit = 1'b0;
        for (t = 0; t < 4; t = t + 1) begin
            @(posedge clk);
            #1;
            if (done) done_seen = done_seen + 1;
        end
        check(done_seen == 1, "case3 done pulses at 3rd count");
        check(counted === 8'd3 && blanker_open === 1'b0, "case3 counted==3 and closed");

        // CASE 4: target_count=0 MUST NEVER open blanker or start watchdog
        @(negedge clk);
        target_count = 8'd0;
        start        = 1'b1;
        @(posedge clk);
        @(negedge clk);
        start        = 1'b0;
        for (t = 0; t < 10; t = t + 1) begin
            @(posedge clk);
            #1;
            check(blanker_open === 1'b0 && busy === 1'b0, "case4 target_count==0 never opens");
        end

        if (errors == 0) begin
            $display("BLANKER_TB_PASS");
            $finish;
        end else begin
            $display("BLANKER_TB_FAIL errors=%0d", errors);
            $fatal(1);
        end
    end
endmodule
