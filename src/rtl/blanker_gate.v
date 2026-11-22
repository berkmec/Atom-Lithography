// blanker_gate.v - counted-implantation gate controller for one beamlet.
// DESIGN.md v2 section 3.3/4: fire ions one at a time; the IBIC detector
// pulses `count_hit` when an ion is registered; the gate closes the blanker
// after the programmed number of counted ions. A watchdog aborts a slot
// whose detector never fires (dead channel / empty beamlet).
//
// Cycle contract (verified against blanker_gate_spec.v by bounded model
// checking, bmc64.ys): start is accepted only in IDLE; blanker_open and busy
// are high exactly in the RUN cycles; completion enters a one-cycle FIN
// state (done=1, blanker closed, start ignored), watchdog expiry a
// one-cycle TO state (abort=1); then back to IDLE. counted holds the last
// sequence count while idle.
`timescale 1ns/1ps
module blanker_gate #(
    parameter WATCHDOG_CYCLES = 100000,   // 1 ms at 100 MHz
    parameter COUNT_W = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire [COUNT_W-1:0]    target_count,
    input  wire                  count_hit,
    output wire                  blanker_open,
    output wire                  busy,
    output wire                  done,
    output wire                  abort,
    output reg  [COUNT_W-1:0]    counted
);
    localparam S_IDLE = 2'd0, S_RUN = 2'd1, S_FIN = 2'd2, S_TO = 2'd3;
    localparam WD_W = (WATCHDOG_CYCLES > 1) ? $clog2(WATCHDOG_CYCLES) : 1;
    reg [1:0]       state;
    reg [WD_W-1:0]  watchdog;

    assign blanker_open = (state == S_RUN);
    assign busy         = (state == S_RUN);
    assign done         = (state == S_FIN);
    assign abort        = (state == S_TO);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= S_IDLE;
            counted  <= {COUNT_W{1'b0}};
            watchdog <= {WD_W{1'b0}};
        end else begin
            case (state)
                S_IDLE: begin
                    if (start) begin
                        counted  <= {COUNT_W{1'b0}};
                        watchdog <= {WD_W{1'b0}};
                        state    <= S_RUN;
                    end
                end
                S_RUN: begin
                    // Saturate at the expiry threshold: only the >= status is
                    // observable, and saturation keeps the narrow counter
                    // equivalent to an unbounded one for every input sequence
                    // (hits can postpone the check past a wrapping point).
                    if (watchdog < WATCHDOG_CYCLES - 1)
                        watchdog <= watchdog + 1'b1;
                    if (count_hit) begin
                        counted <= counted + 1'b1;
                        if (counted + 1'b1 >= target_count)
                            state <= S_FIN;
                    end else if (watchdog >= WATCHDOG_CYCLES - 1) begin
                        state <= S_TO;
                    end
                end
                S_FIN: state <= S_IDLE;
                S_TO:  state <= S_IDLE;
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
