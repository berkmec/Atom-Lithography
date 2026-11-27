// blanker_tile.v - Parameterizable Counted-Implantation Blanker Tile (NCH=8..64)
// One tile drives a beamlet block of the micro ion implanter array
// (DESIGN.md v2 sections 3.3/4; hierarchical NCH=8 SKY130 sub-tiles or NCH=64).
//
// Unified Serial + Parallel Host Interface Contract (matches blanker_array_ctrl.v):
//   1. Parallel CSR interface (direct bench / mezzanine local bus):
//        cfg_we=1, cfg_addr in [0..NCH-1]       -> target_reg[cfg_addr] <= cfg_data
//        cfg_we=1, cfg_addr in [64..64+NCH-1]   -> enable_reg[cfg_addr-64] <= cfg_data[0]
//        (out-of-range addresses when NCH < 64 are cleanly ignored — zero OOB aliasing!)
//        start_all (1-cycle pulse)              -> starts all enabled IDLE channels
//   2. Serial SPI/Frame interface (direct connection to rtl/machine_ctrl/blanker_array_ctrl.v):
//        ser_sel, ser_sclk, ser_sdata           -> shifts NCH enable bits into ser_shift_reg
//        ser_tile_latch_n (falling edge, sel=1) -> commits enable_reg <= ser_shift_reg
//                                                  (auto-sets target_reg=1 if currently 0)
//        ser_frame_latch_n (falling edge)       -> fires unified start_all across enabled channels
//        ser_beam_en (active-HIGH gate)         -> hard-clamps blanker_open to 0 when LOW (interlock)
//        tile_done_out / tile_abort_out         -> aggregated tile feedback -> blanker_array_ctrl
//
// Hardened CDC & Reset Tree:
//   - Single internal 2-FF async-assert / sync-deassert reset synchronizer (`rst_sync_n`)
//     feeds tile control and all NCH child blanker_gate instances with zero release skew.
//   - Per-channel 2-FF IBIC `count_hit` synchronizer + rising-edge detector inside blanker_gate.
//   - Default WATCHDOG_CYCLES = 7,500,000 (75 ms @ 100 MHz >= 5 * 15 ms Poisson tau_shot).
`timescale 1ns/1ps
module blanker_tile #(
    parameter integer NCH             = 64,
    parameter integer WATCHDOG_CYCLES = 7500000,
    parameter integer COUNT_W         = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,

    // Parallel host configuration & status interface
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
    output wire [COUNT_W-1:0]    rd_counted,

    // Unified serial host interface (directly compatible with blanker_array_ctrl.v)
    input  wire                  ser_sel,
    input  wire                  ser_sclk,
    input  wire                  ser_sdata,
    input  wire                  ser_tile_latch_n,
    input  wire                  ser_frame_latch_n,
    input  wire                  ser_beam_en,
    output wire                  tile_done_out,
    output wire                  tile_abort_out
);
    localparam integer CH_W   = (NCH <= 2)  ? 1 :
                                (NCH <= 4)  ? 2 :
                                (NCH <= 8)  ? 3 :
                                (NCH <= 16) ? 4 :
                                (NCH <= 32) ? 5 : 6;
    localparam [7:0] NCH_U8   = NCH[7:0];
    localparam [7:0] EN_HI_U8 = 8'd64 + NCH[7:0];
    localparam [COUNT_W-1:0] ONE_CNT = {{(COUNT_W-1){1'b0}}, 1'b1};

    // Shared 2-FF async-assert / sync-deassert reset synchronizer (eliminates release skew)
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
    wire rst_sync_n = rst_sync_s2;

    // 2-FF CDC synchronizers + edge detectors for serial host control bus
    (* ASYNC_REG = "TRUE" *) reg ser_sel_s1, ser_sel_s2;
    (* ASYNC_REG = "TRUE" *) reg ser_sclk_s1, ser_sclk_s2;
    (* ASYNC_REG = "TRUE" *) reg ser_sdata_s1, ser_sdata_s2;
    (* ASYNC_REG = "TRUE" *) reg ser_tlatch_s1, ser_tlatch_s2;
    (* ASYNC_REG = "TRUE" *) reg ser_flatch_s1, ser_flatch_s2;
    (* ASYNC_REG = "TRUE" *) reg ser_beam_s1, ser_beam_s2;
    reg ser_sclk_prev;
    reg ser_tlatch_prev;
    reg ser_flatch_prev;

    wire ser_sclk_rise   = ser_sclk_s2 & (~ser_sclk_prev);
    wire ser_tlatch_fall = (~ser_tlatch_s2) & ser_tlatch_prev;
    wire ser_flatch_fall = (~ser_flatch_s2) & ser_flatch_prev;
    wire eff_start_all   = start_all | ser_flatch_fall;
    // Fail-safe blanker beam gate: immediate zero if raw ser_beam_en OR synced ser_beam_s2 drops
    wire beam_gate_en    = ser_beam_en & ser_beam_s2;

    reg [NCH-1:0]     ser_shift_reg;
    wire [NCH-1:0]    ser_shift_next;
    generate
        if (NCH > 1) begin : g_ser_multi
            assign ser_shift_next = {ser_sdata_s2, ser_shift_reg[NCH-1:1]};
        end else begin : g_ser_single
            assign ser_shift_next = ser_sdata_s2;
        end
    endgenerate
    reg [COUNT_W-1:0] target_reg [0:NCH-1];
    reg [NCH-1:0]     enable_reg;
    wire [NCH-1:0]    ch_open, ch_busy, ch_done, ch_timeout_abort;
    wire [COUNT_W-1:0] ch_counted [0:NCH-1];

    genvar g;
    generate
        for (g = 0; g < NCH; g = g + 1) begin : ch
            blanker_gate #(
                .WATCHDOG_CYCLES  (WATCHDOG_CYCLES),
                .COUNT_W          (COUNT_W),
                .INTERNAL_RST_SYNC(0)
            ) gate (
                .clk           (clk),
                .rst_n         (rst_sync_n),
                .start         (eff_start_all & enable_reg[g]),
                .target_count  (target_reg[g]),
                .count_hit     (count_hit[g]),
                .blanker_open  (ch_open[g]),
                .busy          (ch_busy[g]),
                .done          (ch_done[g]),
                .timeout_abort (ch_timeout_abort[g]),
                .counted       (ch_counted[g])
            );
            assign blanker_open[g] = ch_open[g] & beam_gate_en;
        end
    endgenerate

    // Safe bounds-checked readback & aggregated tile status outputs
    wire [7:0] rd_addr_u8 = {2'b00, rd_addr};
    wire       rd_in_rng  = (rd_addr_u8 < NCH_U8);
    wire [CH_W-1:0] rd_idx = rd_in_rng ? rd_addr[CH_W-1:0] : {CH_W{1'b0}};

    assign busy_any       = |ch_busy;
    assign rd_counted     = rd_in_rng ? ch_counted[rd_idx] : {COUNT_W{1'b0}};
    assign tile_done_out  = (|enable_reg) && ((done_sticky & enable_reg) == enable_reg);
    assign tile_abort_out = |abort_sticky;

    // Safe bounds-checked parallel configuration decode (eliminates NCH<64 OOB aliasing)
    wire [7:0] cfg_addr_u8 = {1'b0, cfg_addr};
    wire       cfg_is_tgt  = (cfg_addr_u8 < NCH_U8);
    wire       cfg_is_en   = (cfg_addr_u8 >= 8'd64) && (cfg_addr_u8 < EN_HI_U8);
    wire [CH_W-1:0] cfg_ch = cfg_addr[CH_W-1:0];

    // Explicitly sink upper address bits when NCH < 64 for 0 Verilator -Wall warnings
    wire _unused_ok = &{1'b0, cfg_addr[5:0], rd_addr[5:0]};

    integer i;
    always @(posedge clk or negedge rst_sync_n) begin
        if (!rst_sync_n) begin
            ser_sel_s1      <= 1'b0;
            ser_sel_s2      <= 1'b0;
            ser_sclk_s1     <= 1'b0;
            ser_sclk_s2     <= 1'b0;
            ser_sclk_prev   <= 1'b0;
            ser_sdata_s1    <= 1'b0;
            ser_sdata_s2    <= 1'b0;
            ser_tlatch_s1   <= 1'b1;
            ser_tlatch_s2   <= 1'b1;
            ser_tlatch_prev <= 1'b1;
            ser_flatch_s1   <= 1'b1;
            ser_flatch_s2   <= 1'b1;
            ser_flatch_prev <= 1'b1;
            ser_beam_s1     <= 1'b0;
            ser_beam_s2     <= 1'b0;
            ser_shift_reg   <= {NCH{1'b0}};
            enable_reg      <= {NCH{1'b0}};
            done_sticky     <= {NCH{1'b0}};
            abort_sticky    <= {NCH{1'b0}};
            for (i = 0; i < NCH; i = i + 1) target_reg[i] <= {COUNT_W{1'b0}};
        end else begin
            // 2-FF serial bus CDC synchronization
            ser_sel_s1      <= ser_sel;
            ser_sel_s2      <= ser_sel_s1;
            ser_sclk_s1     <= ser_sclk;
            ser_sclk_s2     <= ser_sclk_s1;
            ser_sclk_prev   <= ser_sclk_s2;
            ser_sdata_s1    <= ser_sdata;
            ser_sdata_s2    <= ser_sdata_s1;
            ser_tlatch_s1   <= ser_tile_latch_n;
            ser_tlatch_s2   <= ser_tlatch_s1;
            ser_tlatch_prev <= ser_tlatch_s2;
            ser_flatch_s1   <= ser_frame_latch_n;
            ser_flatch_s2   <= ser_flatch_s1;
            ser_flatch_prev <= ser_flatch_s2;
            ser_beam_s1     <= ser_beam_en;
            ser_beam_s2     <= ser_beam_s1;

            // Serial shift register (ch 0 shifted first -> lands at bit 0 after NCH shifts)
            if (ser_sel_s2 && ser_sclk_rise) begin
                ser_shift_reg <= ser_shift_next;
            end

            // Serial tile latch commits enable bitmap & defaults zero targets to 1 counted ion
            if (ser_sel_s2 && ser_tlatch_fall) begin
                enable_reg <= ser_shift_reg;
                for (i = 0; i < NCH; i = i + 1) begin
                    if (ser_shift_reg[i] && (target_reg[i] == {COUNT_W{1'b0}}))
                        target_reg[i] <= ONE_CNT;
                end
            end

            // Parallel CSR config writes (strictly bounds-checked for NCH <= 64)
            if (cfg_we) begin
                if (cfg_is_tgt)
                    target_reg[cfg_ch] <= cfg_data;
                else if (cfg_is_en)
                    enable_reg[cfg_ch] <= cfg_data[0];
            end

            // Per-channel sticky status updates
            for (i = 0; i < NCH; i = i + 1) begin
                if (eff_start_all && enable_reg[i] && (target_reg[i] != {COUNT_W{1'b0}}) &&
                    !ch_busy[i] && !ch_done[i] && !ch_timeout_abort[i]) begin
                    done_sticky[i]  <= 1'b0;
                    abort_sticky[i] <= 1'b0;
                end else begin
                    if (ch_done[i])          done_sticky[i]  <= 1'b1;
                    if (ch_timeout_abort[i]) abort_sticky[i] <= 1'b1;
                end
            end
        end
    end
endmodule
