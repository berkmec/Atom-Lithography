// blanker_gate_spec.v - INDEPENDENT specification model for equivalence check.
// Written from the DESIGN.md section 3.3/4 behaviour description only:
// "open the blanker on start; count detector hits; close and pulse done when
// the programmed count is reached; pulse abort if no count completes within
// the watchdog window." Deliberately different structure (combinational
// next-state logic, different state encoding) from blanker_gate.v.
`timescale 1ns/1ps
module blanker_gate_spec #(
    parameter WATCHDOG_CYCLES = 100000,
    parameter COUNT_W = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire [COUNT_W-1:0]    target_count,
    input  wire                  count_hit,
    output wire                  blanker_open,
    output wire                  busy,
    output reg                   done,
    output reg                   abort,
    output reg  [COUNT_W-1:0]    counted
);
    localparam IDLE = 2'b00, RUN = 2'b01, FIN = 2'b10, TO = 2'b11;
    reg [1:0]  st, nst;
    reg [31:0] timer, ntimer;
    reg [COUNT_W-1:0] ncounted;

    assign blanker_open = (st == RUN);
    assign busy         = (st == RUN);

    always @* begin
        nst = st; ntimer = timer; ncounted = counted;
        done = 1'b0; abort = 1'b0;
        case (st)
            IDLE: if (start) begin
                ncounted = {COUNT_W{1'b0}}; ntimer = 32'd0; nst = RUN;
            end
            RUN: begin
                ntimer = timer + 32'd1;
                if (count_hit) begin
                    ncounted = counted + 1'b1;
                    if (counted + 1'b1 >= target_count) nst = FIN;
                end else if (timer >= WATCHDOG_CYCLES - 1) begin
                    nst = TO;
                end
            end
            FIN: begin done = 1'b1; nst = IDLE; end
            TO:  begin abort = 1'b1; nst = IDLE; end
            default: nst = IDLE;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= IDLE; timer <= 32'd0; counted <= {COUNT_W{1'b0}};
        end else begin
            st <= nst; timer <= ntimer; counted <= ncounted;
        end
    end
endmodule
