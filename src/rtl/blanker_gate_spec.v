// blanker_gate_spec.v - INDEPENDENT specification model for equivalence check.
// Written from the DESIGN.md section 3.3/4 behaviour description + hardened
// contract: 2-FF async-assert/sync-deassert reset, 2-FF IBIC count_hit sync
// with rising-edge detection (multi-cycle pulse counts once), target_count==0
// rejection, saturating watchdog (default 75 ms @ 100 MHz), and timeout_abort.
`timescale 1ns/1ps
module blanker_gate_spec #(
    parameter integer WATCHDOG_CYCLES   = 7500000,
    parameter integer COUNT_W           = 8,
    parameter integer INTERNAL_RST_SYNC = 1
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire [COUNT_W-1:0]    target_count,
    input  wire                  count_hit,
    output wire                  blanker_open,
    output wire                  busy,
    output reg                   done,
    output reg                   timeout_abort,
    output reg  [COUNT_W-1:0]    counted
);
    localparam [1:0] IDLE = 2'b00;
    localparam [1:0] RUN  = 2'b01;
    localparam [1:0] FIN  = 2'b10;
    localparam [1:0] TO   = 2'b11;

    localparam [31:0] WD_LIM_U32  = WATCHDOG_CYCLES[31:0] - 32'd1;
    localparam [COUNT_W-1:0] ONE_C = {{(COUNT_W-1){1'b0}}, 1'b1};

    wire rst_sync_n;
    generate
        if (INTERNAL_RST_SYNC != 0) begin : g_spec_rst_sync
            (* ASYNC_REG = "TRUE" *) reg rst_s1;
            (* ASYNC_REG = "TRUE" *) reg rst_s2;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    rst_s1 <= 1'b0;
                    rst_s2 <= 1'b0;
                end else begin
                    rst_s1 <= 1'b1;
                    rst_s2 <= rst_s1;
                end
            end
            assign rst_sync_n = rst_s2;
        end else begin : g_spec_rst_ext
            assign rst_sync_n = rst_n;
        end
    endgenerate

    (* ASYNC_REG = "TRUE" *) reg hit_s1, hit_s2;
    reg hit_prev;
    wire hit_rise = hit_s2 & (~hit_prev);

    reg [1:0]         st, nst;
    reg [31:0]        timer, ntimer;
    reg [COUNT_W-1:0] ncounted;

    assign blanker_open = (st == RUN);
    assign busy         = (st == RUN);

    always @* begin
        nst           = st;
        ntimer        = timer;
        ncounted      = counted;
        done          = 1'b0;
        timeout_abort = 1'b0;
        case (st)
            IDLE: begin
                if (start && (target_count != {COUNT_W{1'b0}})) begin
                    ncounted = {COUNT_W{1'b0}};
                    ntimer   = 32'd0;
                    nst      = RUN;
                end
            end
            RUN: begin
                if (timer < WD_LIM_U32)
                    ntimer = timer + 32'd1;
                if (hit_rise) begin
                    ncounted = counted + ONE_C;
                    if ((counted + ONE_C) >= target_count)
                        nst = FIN;
                end else if (timer >= WD_LIM_U32) begin
                    nst = TO;
                end
            end
            FIN: begin
                done = 1'b1;
                nst  = IDLE;
            end
            TO: begin
                timeout_abort = 1'b1;
                nst           = IDLE;
            end
            default: nst = IDLE;
        endcase
    end

    always @(posedge clk or negedge rst_sync_n) begin
        if (!rst_sync_n) begin
            hit_s1   <= 1'b0;
            hit_s2   <= 1'b0;
            hit_prev <= 1'b0;
            st       <= IDLE;
            timer    <= 32'd0;
            counted  <= {COUNT_W{1'b0}};
        end else begin
            hit_s1   <= count_hit;
            hit_s2   <= hit_s1;
            hit_prev <= hit_s2;
            st       <= nst;
            timer    <= ntimer;
            counted  <= ncounted;
        end
    end
endmodule
