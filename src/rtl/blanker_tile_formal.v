// Formal property wrapper for blanker_tile (small instance).
// Properties checked by yosys SAT (tile_formal.ys):
//  P1: a channel's blanker is never open while its done_sticky is set
//  P2: a channel's blanker is never open while its abort_sticky is set
//  P3: done_sticky and abort_sticky are never set together for a channel
`timescale 1ns/1ps
module blanker_tile_formal (
    input wire clk, input wire rst_n,
    input wire cfg_we, input wire [6:0] cfg_addr, input wire [7:0] cfg_data,
    input wire start_all, input wire [1:0] count_hit, input wire [5:0] rd_addr
);
    wire [1:0] open_, done_st, abort_st;
    wire busy_any;
    wire [7:0] rd_counted;
    blanker_tile #(.NCH(2), .WATCHDOG_CYCLES(6), .COUNT_W(8)) dut (
        .clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start_all(start_all), .count_hit(count_hit),
        .blanker_open(open_), .busy_any(busy_any),
        .done_sticky(done_st), .abort_sticky(abort_st),
        .rd_addr(rd_addr), .rd_counted(rd_counted)
    );
    reg seen_reset;
    initial seen_reset = 1'b0;
    always @(posedge clk) if (!rst_n) seen_reset <= 1'b1;
    integer i;
    always @(posedge clk) begin
        if (rst_n && seen_reset) begin
            for (i = 0; i < 2; i = i + 1) begin
                assert(!(open_[i] && done_st[i]));
                assert(!(open_[i] && abort_st[i]));
                assert(!(done_st[i] && abort_st[i]));
            end
        end
    end
endmodule
