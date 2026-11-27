// blanker_array_ctrl.v - 32x32 (1,024-ch, 16x64 tile) Electrostatic Beamlet Blanker Controller
// BOM Traceability: S2.2-01, S2.4-01, S2.4-02, S3.3-01, S3.3-02
// Target Clock    : 100.0 MHz (10.0 ns period) — FPGA Machine Control Brain
//
// Unified Serial/Counted-Ion Interface Contract (directly matches src/rtl/blanker_tile.v):
//   - Shifts 16 tiles x 64 channels/tile enable mask over (tile_sel[3:0], tile_sclk,
//     tile_sdata, tile_latch_n, frame_latch_n) + hard-gated tile_beam_en[15:0].
//   - On frame_latch_n falling edge, each blanker_tile starts counted single-ion
//     implantation with per-channel IBIC count_hit feedback; tile_done_in[15:0] &
//     tile_abort_in[15:0] are 2-FF CDC-synchronized back into sticky aggregators.
//   - Internal 2-FF async-assert / sync-deassert reset synchronizer (rst_sync_n).
//   - Hard-wired asynchronous-priority + 1-clock synchronous `interlock_blank_force` override.
//
// Synthesis Hygiene: ZERO latches, ZERO combinational '/', ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module blanker_array_ctrl (
    input  wire        clk,
    input  wire        rst_n,

    // Hard-wired safety interlock override (active-HIGH = FORCE SAFE BLANKED)
    input  wire        interlock_blank_force,

    // Control & configuration inputs (from CSR / host)
    input  wire        frame_start,
    input  wire        sticky_clr,
    input  wire        interlock_clr,
    input  wire        auto_offset_en,
    input  wire [15:0] sclk_div,
    input  wire signed [15:0] dx_pitch,
    input  wire signed [15:0] dy_pitch,
    input  wire [15:0] tile_en_mask,

    // 1,024-bit Pattern & Dead-Channel Mask Memory R/W Port (32 rows x 32 bits)
    input  wire        mem_we,
    input  wire        mem_bank_sel,   // 0 = pattern_mem, 1 = dead_mask_mem
    input  wire [4:0]  mem_row_addr,
    input  wire [31:0] mem_wdata,
    output reg  [31:0] mem_rdata,

    // Tile feedback inputs (16 x 64-ch blanker ASIC tiles, 2-FF CDC synced internally)
    input  wire [15:0] tile_done_in,
    input  wire [15:0] tile_abort_in,

    // Physical Blanker Array Serial & Hardware Gate Outputs
    output reg  [3:0]  tile_sel,
    output reg         tile_sclk,
    output wire        tile_sdata,
    output reg         tile_latch_n,
    output reg         frame_latch_n,
    output wire [15:0] tile_beam_en,

    // Status & telemetry outputs
    output wire        busy,
    output wire        safe_blanked,
    output reg         interlock_latched,
    output reg         frame_done_sticky,
    output reg         interlock_abort_sticky,
    output reg  [15:0] tile_done_sticky,
    output reg  [15:0] tile_abort_sticky,
    output wire        any_tile_abort,
    output wire        all_tiles_done,
    output reg  [10:0] active_unblank_cnt,
    output wire signed [15:0] stitch_dx_pitch_out,
    output wire signed [15:0] stitch_dy_pitch_out
);
    // FSM state encoding
    localparam [2:0] ST_IDLE        = 3'd0;
    localparam [2:0] ST_FETCH       = 3'd1;
    localparam [2:0] ST_SHIFT_LOW   = 3'd2;
    localparam [2:0] ST_SHIFT_HIGH  = 3'd3;
    localparam [2:0] ST_TILE_LATCH  = 3'd4;
    localparam [2:0] ST_FRAME_LATCH = 3'd5;
    localparam [2:0] ST_INTERLOCK   = 3'd6;

    // 2-FF async-assert / sync-deassert reset synchronizer
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

    // 2-FF CDC synchronizers for tile feedback crossing from -5 kV mezzanine deck
    (* ASYNC_REG = "TRUE" *) reg [15:0] tile_done_s1;
    (* ASYNC_REG = "TRUE" *) reg [15:0] tile_done_s2;
    (* ASYNC_REG = "TRUE" *) reg [15:0] tile_abort_s1;
    (* ASYNC_REG = "TRUE" *) reg [15:0] tile_abort_s2;

    // 32x32 = 1,024-bit Pattern RAM and 1,024-bit Dead-Channel Mask RAM
    reg [31:0] pattern_mem   [0:31];
    reg [31:0] dead_mask_mem [0:31];

    // Internal registered outputs (gated by hard-wired interlock clamp below)
    reg        r_tile_sdata;
    reg [15:0] r_tile_beam_en;

    // Serializer FSM registers
    reg [2:0]  state;
    reg [3:0]  cur_tile;      // 0..15 (tile_row = cur_tile[3:2], tile_col = cur_tile[1:0])
    reg [5:0]  cur_ch;        // 0..63 (sub_row  = cur_ch[5:3],   sub_col  = cur_ch[2:0])
    reg [15:0] div_cnt;
    reg [10:0] unblank_accum;
    reg [31:0] pat_row_q;
    reg [31:0] mask_row_q;
    reg        src_in_bounds_q;
    reg [4:0]  src_col_q;
    reg [4:0]  phys_col_q;

    // Hard-wired fail-safe override
    wire force_blank_now = interlock_blank_force | interlock_latched;

    assign tile_sdata          = force_blank_now ? 1'b0     : r_tile_sdata;
    assign tile_beam_en        = force_blank_now ? 16'h0000 : r_tile_beam_en;
    assign safe_blanked        = force_blank_now | (~(|r_tile_beam_en));
    assign busy                = (state != ST_IDLE) && (state != ST_INTERLOCK);
    assign any_tile_abort      = |tile_abort_sticky;
    assign all_tiles_done      = (tile_en_mask != 16'h0000) &&
                                 ((tile_done_sticky & tile_en_mask) == tile_en_mask);
    assign stitch_dx_pitch_out = dx_pitch;
    assign stitch_dy_pitch_out = dy_pitch;

    // Effective divider floor (>= 16'd1 -> min half-period 1 clock)
    wire [15:0] div_limit = (sclk_div == 16'd0) ? 16'd0 : (sclk_div - 16'd1);

    // Physical (row, col) derived from 16 x (8x8) tile geometry
    wire [4:0] phys_row = {cur_tile[3:2], cur_ch[5:3]};
    wire [4:0] phys_col = {cur_tile[1:0], cur_ch[2:0]};

    // Signed step-and-stitch source coordinate computation
    wire signed [16:0] s_phys_row = {12'sd0, phys_row};
    wire signed [16:0] s_phys_col = {12'sd0, phys_col};
    wire signed [16:0] s_dy_ext   = {dy_pitch[15], dy_pitch};
    wire signed [16:0] s_dx_ext   = {dx_pitch[15], dx_pitch};
    wire signed [16:0] s_src_row  = auto_offset_en ? (s_phys_row - s_dy_ext) : s_phys_row;
    wire signed [16:0] s_src_col  = auto_offset_en ? (s_phys_col - s_dx_ext) : s_phys_col;

    wire src_row_ok = (s_src_row >= 17'sd0) && (s_src_row <= 17'sd31);
    wire src_col_ok = (s_src_col >= 17'sd0) && (s_src_col <= 17'sd31);
    wire src_ok     = src_row_ok && src_col_ok;
    wire [4:0] src_row_idx = src_row_ok ? s_src_row[4:0] : 5'd0;
    wire [4:0] src_col_idx = src_col_ok ? s_src_col[4:0] : 5'd0;

    wire raw_pat_bit  = src_in_bounds_q ? pat_row_q[src_col_q] : 1'b0;
    wire dead_bit     = mask_row_q[phys_col_q];
    wire tile_enabled = tile_en_mask[cur_tile];
    wire ch_unblank   = raw_pat_bit & (~dead_bit) & tile_enabled & (~force_blank_now);

    integer k;

    always @(posedge clk) begin
        if (!rst_sync_n) begin
            tile_done_s1           <= 16'h0000;
            tile_done_s2           <= 16'h0000;
            tile_abort_s1          <= 16'h0000;
            tile_abort_s2          <= 16'h0000;
            state                  <= ST_IDLE;
            cur_tile               <= 4'd0;
            cur_ch                 <= 6'd0;
            div_cnt                <= 16'd0;
            unblank_accum          <= 11'd0;
            active_unblank_cnt     <= 11'd0;
            pat_row_q              <= 32'd0;
            mask_row_q             <= 32'd0;
            src_in_bounds_q        <= 1'b0;
            src_col_q              <= 5'd0;
            phys_col_q             <= 5'd0;
            tile_sel               <= 4'd0;
            tile_sclk              <= 1'b0;
            r_tile_sdata           <= 1'b0;
            tile_latch_n           <= 1'b1;
            frame_latch_n          <= 1'b1;
            r_tile_beam_en         <= 16'h0000;
            interlock_latched      <= 1'b0;
            frame_done_sticky      <= 1'b0;
            interlock_abort_sticky <= 1'b0;
            tile_done_sticky       <= 16'h0000;
            tile_abort_sticky      <= 16'h0000;
            mem_rdata              <= 32'd0;
            for (k = 0; k < 32; k = k + 1) begin
                pattern_mem[k]   <= 32'd0;
                dead_mask_mem[k] <= 32'd0;
            end
        end else begin
            // 2-FF CDC sync on tile feedback
            tile_done_s1  <= tile_done_in;
            tile_done_s2  <= tile_done_s1;
            tile_abort_s1 <= tile_abort_in;
            tile_abort_s2 <= tile_abort_s1;

            // CSR Memory Read/Write
            if (mem_we) begin
                if (mem_bank_sel) begin
                    dead_mask_mem[mem_row_addr] <= mem_wdata;
                end else begin
                    pattern_mem[mem_row_addr] <= mem_wdata;
                end
            end
            mem_rdata <= mem_bank_sel ? dead_mask_mem[mem_row_addr] : pattern_mem[mem_row_addr];

            // Sticky Tile Done / Abort Aggregator (from 2-FF synced feedback)
            if (sticky_clr) begin
                tile_done_sticky  <= 16'h0000;
                tile_abort_sticky <= 16'h0000;
                frame_done_sticky <= 1'b0;
            end else begin
                tile_done_sticky  <= tile_done_sticky | tile_done_s2;
                tile_abort_sticky <= tile_abort_sticky | tile_abort_s2;
            end

            // Hard-wired highest-priority interlock trip handling
            if (interlock_blank_force) begin
                interlock_latched      <= 1'b1;
                interlock_abort_sticky <= 1'b1;
                r_tile_beam_en         <= 16'h0000;
                r_tile_sdata           <= 1'b0;
                tile_sclk              <= 1'b0;
                tile_latch_n           <= 1'b1;
                frame_latch_n          <= 1'b1;
                div_cnt                <= 16'd0;
                state                  <= ST_INTERLOCK;
            end else begin
                case (state)
                    ST_INTERLOCK: begin
                        r_tile_beam_en <= 16'h0000;
                        r_tile_sdata   <= 1'b0;
                        tile_sclk      <= 1'b0;
                        tile_latch_n   <= 1'b1;
                        frame_latch_n  <= 1'b1;
                        if (interlock_clr) begin
                            interlock_latched      <= 1'b0;
                            interlock_abort_sticky <= 1'b0;
                            state                  <= ST_IDLE;
                        end
                    end

                    ST_IDLE: begin
                        tile_sclk     <= 1'b0;
                        tile_latch_n  <= 1'b1;
                        frame_latch_n <= 1'b1;
                        if (interlock_clr) begin
                            interlock_latched      <= 1'b0;
                            interlock_abort_sticky <= 1'b0;
                        end
                        if (frame_start && !interlock_latched) begin
                            cur_tile          <= 4'd0;
                            cur_ch            <= 6'd0;
                            div_cnt           <= 16'd0;
                            unblank_accum     <= 11'd0;
                            tile_sel          <= 4'd0;
                            r_tile_beam_en    <= 16'h0000;
                            frame_done_sticky <= 1'b0;
                            tile_done_sticky  <= 16'h0000;
                            tile_abort_sticky <= 16'h0000;
                            state             <= ST_FETCH;
                        end
                    end

                    ST_FETCH: begin
                        tile_sel        <= cur_tile;
                        pat_row_q       <= pattern_mem[src_row_idx];
                        mask_row_q      <= dead_mask_mem[phys_row];
                        src_in_bounds_q <= src_ok;
                        src_col_q       <= src_col_idx;
                        phys_col_q      <= phys_col;
                        tile_sclk       <= 1'b0;
                        tile_latch_n    <= 1'b1;
                        div_cnt         <= 16'd0;
                        state           <= ST_SHIFT_LOW;
                    end

                    ST_SHIFT_LOW: begin
                        r_tile_sdata <= ch_unblank;
                        tile_sclk    <= 1'b0;
                        if (div_cnt == div_limit) begin
                            div_cnt   <= 16'd0;
                            tile_sclk <= 1'b1;
                            if (ch_unblank) begin
                                unblank_accum <= unblank_accum + 11'd1;
                            end
                            state <= ST_SHIFT_HIGH;
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    ST_SHIFT_HIGH: begin
                        tile_sclk <= 1'b1;
                        if (div_cnt == div_limit) begin
                            div_cnt   <= 16'd0;
                            tile_sclk <= 1'b0;
                            if (cur_ch == 6'd63) begin
                                tile_latch_n <= 1'b0;
                                state        <= ST_TILE_LATCH;
                            end else begin
                                cur_ch <= cur_ch + 6'd1;
                                state  <= ST_FETCH;
                            end
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    ST_TILE_LATCH: begin
                        tile_latch_n <= 1'b0;
                        if (div_cnt == div_limit) begin
                            div_cnt      <= 16'd0;
                            tile_latch_n <= 1'b1;
                            if (cur_tile == 4'd15) begin
                                frame_latch_n <= 1'b0;
                                state         <= ST_FRAME_LATCH;
                            end else begin
                                cur_tile <= cur_tile + 4'd1;
                                cur_ch   <= 6'd0;
                                state    <= ST_FETCH;
                            end
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    ST_FRAME_LATCH: begin
                        frame_latch_n <= 1'b0;
                        if (div_cnt == div_limit) begin
                            div_cnt            <= 16'd0;
                            frame_latch_n      <= 1'b1;
                            r_tile_sdata       <= 1'b0;
                            active_unblank_cnt <= unblank_accum;
                            r_tile_beam_en     <= tile_en_mask;
                            frame_done_sticky  <= 1'b1;
                            state              <= ST_IDLE;
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    default: begin
                        r_tile_beam_en <= 16'h0000;
                        r_tile_sdata   <= 1'b0;
                        state          <= ST_INTERLOCK;
                    end
                endcase
            end
        end
    end
endmodule
