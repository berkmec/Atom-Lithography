// blanker_tile.v - 64-channel counted-implantation blanker tile.
// One tile drives an 8x8 beamlet block of the micro ion implanter array
// (DESIGN.md v2 sections 3.3/4). Each channel is the BMC-verified
// blanker_gate; this module adds the host interface:
//
//   config writes (cfg_we):
//     cfg_addr 0..63    -> target ion count for channel cfg_addr
//     cfg_addr 64..127  -> enable bit for channel cfg_addr-64 = cfg_data[0]
//   start_all (1-cycle pulse): starts every enabled channel that is IDLE
//     (busy channels are unaffected, matching blanker_gate's contract);
//     starting a channel clears its done/abort sticky bits.
//   status: done_sticky / abort_sticky bitmaps for host polling;
//     rd_addr selects one channel's live ion counter on rd_counted.
//
// Sticky semantics are pinned by tests/test_blanker_tile.py.
`timescale 1ns/1ps
module blanker_tile #(
    parameter NCH = 64,
    parameter WATCHDOG_CYCLES = 100000,
    parameter COUNT_W = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  cfg_we,
    input  wire [6:0]            cfg_addr,
    input  wire [COUNT_W-1:0]    cfg_data,
    input  wire                  start_all,
    input  wire [NCH-1:0]        count_hit,
    output wire [NCH-1:0]        blanker_open,
    output wire                  busy_any,
    output reg  [NCH-1:0]        done_sticky,
    output reg  [NCH-1:0]        abort_sticky,
    input  wire [5:0]            rd_addr,
    output wire [COUNT_W-1:0]    rd_counted
);
    reg [COUNT_W-1:0] target_reg [0:NCH-1];
    reg [NCH-1:0]     enable_reg;
    wire [NCH-1:0]    ch_busy, ch_done, ch_abort;
    wire [COUNT_W-1:0] ch_counted [0:NCH-1];

    genvar g;
    generate
        for (g = 0; g < NCH; g = g + 1) begin : ch
            blanker_gate #(.WATCHDOG_CYCLES(WATCHDOG_CYCLES), .COUNT_W(COUNT_W)) gate (
                .clk(clk), .rst_n(rst_n),
                .start(start_all & enable_reg[g]),
                .target_count(target_reg[g]),
                .count_hit(count_hit[g]),
                .blanker_open(blanker_open[g]),
                .busy(ch_busy[g]), .done(ch_done[g]), .abort(ch_abort[g]),
                .counted(ch_counted[g])
            );
        end
    endgenerate

    assign busy_any   = |ch_busy;
    assign rd_counted = ch_counted[rd_addr];

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            enable_reg   <= {NCH{1'b0}};
            done_sticky  <= {NCH{1'b0}};
            abort_sticky <= {NCH{1'b0}};
            for (i = 0; i < NCH; i = i + 1) target_reg[i] <= {COUNT_W{1'b0}};
        end else begin
            if (cfg_we) begin
                if (cfg_addr < NCH)
                    target_reg[cfg_addr[5:0]] <= cfg_data;
                else
                    enable_reg[cfg_addr[5:0]] <= cfg_data[0];
            end
            for (i = 0; i < NCH; i = i + 1) begin
                if (start_all & enable_reg[i] & ~ch_busy[i] & ~ch_done[i] & ~ch_abort[i]) begin
                    done_sticky[i]  <= 1'b0;
                    abort_sticky[i] <= 1'b0;
                end else begin
                    if (ch_done[i])  done_sticky[i]  <= 1'b1;
                    if (ch_abort[i]) abort_sticky[i] <= 1'b1;
                end
            end
        end
    end
endmodule
