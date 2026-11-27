// blanker_gate.v - counted-implantation gate controller for one beamlet.
// DESIGN.md v2 section 3.3/4: fire ions one at a time; the IBIC detector
// pulses `count_hit` when an ion is registered; the gate closes the blanker
// after the programmed number of counted ions. A watchdog aborts a slot
// whose detector never fires (dead channel / empty beamlet).
//
// Hardened RTL contract:
//   - Default WATCHDOG_CYCLES = 7,500,000 (75 ms @ 100 MHz >= 5 * tau_shot
//     for canonical 15 ms Poisson single-ion cycle -> <0.67% truncation).
//   - Built-in 2-FF async-assert / sync-deassert reset synchronizer
//     (INTERNAL_RST_SYNC=1 default; set 0 when driven by parent reset bridge).
//   - Built-in 2-FF CDC synchronizer + rising-edge detector on `count_hit`
//     so multi-cycle (e.g., 30 ns / 3-clock) IBIC pulses count exactly once.
//   - `target_count == 0` guard: start is ignored and blanker never opens.
//   - Port `timeout_abort` avoids SV/C++ reserved keyword `abort` (0 Verilator -Wall warnings).
`timescale 1ns/1ps
module blanker_gate #(
    parameter integer WATCHDOG_CYCLES   = 7500000, // 75 ms @ 100 MHz (>= 5 * 15 ms tau_shot)
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
    output wire                  done,
    output wire                  timeout_abort,
    output reg  [COUNT_W-1:0]    counted
);
    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_RUN  = 2'd1;
    localparam [1:0] S_FIN  = 2'd2;
    localparam [1:0] S_TO   = 2'd3;

    localparam integer WD_W      = (WATCHDOG_CYCLES > 1) ? $clog2(WATCHDOG_CYCLES) : 1;
    localparam integer WD_MAX_I  = (WATCHDOG_CYCLES > 1) ? (WATCHDOG_CYCLES - 1) : 0;
    localparam [WD_W-1:0] WD_MAX = WD_MAX_I[WD_W-1:0];
    localparam [WD_W-1:0] WD_ONE = {{(WD_W-1){1'b0}}, 1'b1};
    localparam [COUNT_W-1:0] CNT_ONE = {{(COUNT_W-1){1'b0}}, 1'b1};

    // 2-FF async-assert / sync-deassert reset synchronizer
    wire rst_sync_n;
    generate
        if (INTERNAL_RST_SYNC != 0) begin : g_rst_sync
            (* ASYNC_REG = "TRUE" *) reg rst_sync_s1;
            (* ASYNC_REG = "TRUE" *) reg rst_sync_s2;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    rst_sync_s1 <= 1'b0;
                    rst_sync_s2 <= 1'b0;
                end else begin
                    rst_sync_s1 <= 1'b1;
                    rst_sync_s2 <= rst_sync_s1;
                end
            end
            assign rst_sync_n = rst_sync_s2;
        end else begin : g_rst_ext
            assign rst_sync_n = rst_n;
        end
    endgenerate

    // 2-FF CDC synchronizer + rising-edge detector on async IBIC count_hit input
    (* ASYNC_REG = "TRUE" *) reg count_hit_s1;
    (* ASYNC_REG = "TRUE" *) reg count_hit_s2;
    reg count_hit_prev;
    wire count_hit_rise = count_hit_s2 & (~count_hit_prev);

    reg [1:0]       state;
    reg [WD_W-1:0]  watchdog;

    assign blanker_open  = (state == S_RUN);
    assign busy          = (state == S_RUN);
    assign done          = (state == S_FIN);
    assign timeout_abort = (state == S_TO);

    always @(posedge clk or negedge rst_sync_n) begin
        if (!rst_sync_n) begin
            count_hit_s1   <= 1'b0;
            count_hit_s2   <= 1'b0;
            count_hit_prev <= 1'b0;
            state          <= S_IDLE;
            counted        <= {COUNT_W{1'b0}};
            watchdog       <= {WD_W{1'b0}};
        end else begin
            count_hit_s1   <= count_hit;
            count_hit_s2   <= count_hit_s1;
            count_hit_prev <= count_hit_s2;

            case (state)
                S_IDLE: begin
                    // Reject target_count == 0: blanker must never open for 0-ion target
                    if (start && (target_count != {COUNT_W{1'b0}})) begin
                        counted  <= {COUNT_W{1'b0}};
                        watchdog <= {WD_W{1'b0}};
                        state    <= S_RUN;
                    end
                end
                S_RUN: begin
                    // Saturate watchdog at WD_MAX to prevent wrap-around under continuous hits
                    if (watchdog < WD_MAX)
                        watchdog <= watchdog + WD_ONE;
                    if (count_hit_rise) begin
                        counted <= counted + CNT_ONE;
                        if ((counted + CNT_ONE) >= target_count)
                            state <= S_FIN;
                    end else if (watchdog >= WD_MAX) begin
                        state <= S_TO;
                    end
                end
                S_FIN:   state <= S_IDLE;
                S_TO:    state <= S_IDLE;
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
