// Bounded model-check miter: DUT vs independent spec model, same inputs.
`timescale 1ns/1ps
module blanker_miter (
    input wire clk,
    input wire rst_n,
    input wire start,
    input wire [7:0] target_count,
    input wire count_hit
);
    wire b1, u1, d1, a1, b2, u2, d2, a2;
    wire [7:0] c1, c2;
    blanker_gate #(.WATCHDOG_CYCLES(50)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .target_count(target_count),
        .count_hit(count_hit), .blanker_open(b1), .busy(u1), .done(d1),
        .timeout_abort(a1), .counted(c1));
    blanker_gate_spec #(.WATCHDOG_CYCLES(50)) spec (
        .clk(clk), .rst_n(rst_n), .start(start), .target_count(target_count),
        .count_hit(count_hit), .blanker_open(b2), .busy(u2), .done(d2),
        .timeout_abort(a2), .counted(c2));
    always @(posedge clk) begin
        if (rst_n) begin
            assert(b1 == b2);
            assert(u1 == u2);
            assert(d1 == d2);
            assert(a1 == a2);
            assert(c1 == c2);
        end
    end
endmodule
