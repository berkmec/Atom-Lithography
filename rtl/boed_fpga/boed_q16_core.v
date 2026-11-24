// boed_q16_core.v - Synthesizable 4-Lane SIMD Q16.16 Bayesian Spectroscopy & SPRT Accelerator
// Target: Xilinx Zynq UltraScale+ RFSoC ZU48DR @ 250 MHz (4.0 ns period)
// Cycle-exact match to src/machine_control/fpga_boed_dsp.py (Exp140 / Exp149):
//   - Stage-0 SPRT fast-abort unit: 4 clock cycles (16.0 ns) per shot LLR update
//   - Stage-2 BOED 1001-bin grid filter (P=4 SIMD lanes):
//       S_PASS1 = 263 cycles (251 4-lane sweep beats + 12 pipeline drain cycles)
//       S_PASS2 = 265 cycles (251 4-lane sweep beats + 14 pipeline drain cycles)
//       S_POST  =  56 cycles (3 parallel bit-serial restoring dividers + 16-stage isqrt + Fisher argmax)
//       TOTAL   = 584 clock cycles = 2.336 us @ 250 MHz!
//
// Synthesis hygiene (verified with Verilator --lint-only -Wall, Icarus Verilog vvp, and Yosys):
//   - ZERO combinational `/` division operators anywhere in RTL (real shift-subtract restoring dividers)
//   - Clean combinational 4-way comparator tree for max_lp_reg (zero racy multi-NBA updates)
//   - Exact 1-cycle BRAM read alignment in S_PASS2 (zero dropped/shifted beats)
//   - Pipelined S_PASS2 MAC (pre-registered df^2 -> product register -> pairwise adder -> 48b accumulate)
//   - Full 64-bit/36-bit safe moment variance arithmetic (zero 32-bit overflow at grid edges)
`timescale 1ns/1ps

module boed_q16_core #(
    parameter integer N_FINE_BINS      = 1001,
    parameter integer SIMD_LANES       = 4,
    parameter integer BIN_STEP_HZ      = 10,
    parameter integer SWEEP_BEATS      = 251, // ceil(1001 / 4)
    parameter integer PIPE_PASS1_CYC   = 12,
    parameter integer PIPE_PASS2_CYC   = 14,
    parameter integer POST_CYC         = 56,
    parameter         LOR_HEX_FILE     = "rom_loglik_p0.hex",
    parameter         EXP_HEX_FILE     = "rom_loglik_p1.hex"
) (
    input  wire               clk,
    input  wire               rst_n,

    // Stage-0 SPRT fast-abort interface (4 cycles = 16 ns)
    input  wire               sprt_start,
    input  wire               sprt_reset_llr,
    input  wire signed [31:0] sprt_y_q16,
    input  wire signed [31:0] sprt_half_sig_q16,
    input  wire signed [31:0] sprt_scale_q16,
    input  wire signed [31:0] sprt_thresh_q16,
    output reg                sprt_done,
    output reg                sprt_decision_valid,
    output reg                sprt_donor_present,
    output reg  signed [31:0] sprt_llr_q16,

    // Stage-2 BOED step interface (584 cycles = 2.336 us @ 250 MHz)
    input  wire               step_start,
    input  wire               prior_load_en,
    input  wire        [9:0]  prior_load_addr,
    input  wire signed [31:0] prior_load_lp_q16,
    input  wire signed [31:0] f_init_hz,
    input  wire signed [31:0] f_probe_hz,
    input  wire signed [31:0] y_meas_q16,
    input  wire        [31:0] inv_gamma_q24,
    input  wire signed [31:0] inv_2var_q16,
    input  wire        [15:0] delta_fisher_q4,
    input  wire        [15:0] max_off_q4,
    input  wire        [7:0]  step_idx,

    output wire               busy,
    output reg                step_done,
    output reg  signed [31:0] mu_off_q8,
    output reg         [15:0] std_q4,
    output reg  signed [31:0] next_probe_off_q8,
    output reg         [15:0] cycle_count
);
    // Exact FSM state encoding & cycle limits (263 + 265 + 56 = 584 cycles = 2.336 us @ 250 MHz)
    localparam [1:0] S_IDLE  = 2'd0;
    localparam [1:0] S_PASS1 = 2'd1;
    localparam [1:0] S_PASS2 = 2'd2;
    localparam [1:0] S_POST  = 2'd3;

    localparam [9:0]  SWEEP_BEATS_U10 = SWEEP_BEATS[9:0];
    localparam [9:0]  PASS1_LIMIT     = SWEEP_BEATS[9:0] + PIPE_PASS1_CYC[9:0]; // 263
    localparam [9:0]  PASS2_LIMIT     = SWEEP_BEATS[9:0] + PIPE_PASS2_CYC[9:0]; // 265
    localparam [9:0]  POST_LIMIT      = POST_CYC[9:0];                          //  56
    localparam [10:0] N_FINE_BINS_U11 = N_FINE_BINS[10:0];
    localparam signed [31:0] BIN_STEP_S32  = BIN_STEP_HZ[31:0];
    localparam signed [31:0] INT32_MIN_VAL = -32'sd2147483647 - 32'sd1;
    localparam signed [31:0] INT32_MAX_VAL =  32'sd2147483647;

    // -----------------------------------------------------------------------
    // 1. Stage-0 SPRT 4-Cycle Pipelined Engine (16 ns @ 250 MHz)
    // -----------------------------------------------------------------------
    reg        [2:0]  sprt_pipe_v;
    reg signed [31:0] sprt_diff_s1;
    reg signed [31:0] sprt_scale_s1;
    reg signed [31:0] sprt_thr_s1;
    reg signed [63:0] sprt_prod_s2;
    reg signed [31:0] sprt_thr_s2;
    reg signed [31:0] sprt_delta_s3;
    reg signed [31:0] sprt_thr_s3;

    wire signed [63:0] sprt_round_s2 = sprt_prod_s2 + 64'sd32768;
    wire signed [31:0] sprt_llr_next = sprt_llr_q16 + sprt_delta_s3;

    always @(posedge clk) begin
        if (!rst_n) begin
            sprt_pipe_v         <= 3'b000;
            sprt_diff_s1        <= 32'sd0;
            sprt_scale_s1       <= 32'sd0;
            sprt_thr_s1         <= 32'sd0;
            sprt_prod_s2        <= 64'sd0;
            sprt_thr_s2         <= 32'sd0;
            sprt_delta_s3       <= 32'sd0;
            sprt_thr_s3         <= 32'sd0;
            sprt_llr_q16        <= 32'sd0;
            sprt_done           <= 1'b0;
            sprt_decision_valid <= 1'b0;
            sprt_donor_present  <= 1'b0;
        end else begin
            // Cycle 1: subtract half-signal threshold
            sprt_pipe_v[0] <= sprt_start;
            sprt_diff_s1   <= sprt_y_q16 - sprt_half_sig_q16;
            sprt_scale_s1  <= sprt_scale_q16;
            sprt_thr_s1    <= sprt_thresh_q16;

            // Cycle 2: DSP48E2 signed multiply
            sprt_pipe_v[1] <= sprt_pipe_v[0];
            sprt_prod_s2   <= {{32{sprt_diff_s1[31]}}, sprt_diff_s1} * {{32{sprt_scale_s1[31]}}, sprt_scale_s1};
            sprt_thr_s2    <= sprt_thr_s1;

            // Cycle 3: Q16.16 round-to-nearest shift
            sprt_pipe_v[2] <= sprt_pipe_v[1];
            sprt_delta_s3  <= $signed(sprt_round_s2[47:16]);
            sprt_thr_s3    <= sprt_thr_s2;

            // Cycle 4: LLR accumulate + threshold compare
            sprt_done <= sprt_pipe_v[2];
            if (sprt_reset_llr) begin
                sprt_llr_q16        <= 32'sd0;
                sprt_decision_valid <= 1'b0;
                sprt_donor_present  <= 1'b0;
            end else if (sprt_pipe_v[2]) begin
                sprt_llr_q16        <= sprt_llr_next;
                sprt_decision_valid <= (sprt_llr_next >= sprt_thr_s3) ||
                                       (sprt_llr_next <= -sprt_thr_s3);
                sprt_donor_present  <= (sprt_llr_next > 32'sd0);
            end
        end
    end

    // -----------------------------------------------------------------------
    // 2. Stage-2 BOED 4-Bank Synchronous Posterior SRAM (4 x 256 x 32-bit BRAM)
    //    Clean simple dual-port template (no reset on BRAM read register)
    //    so Yosys & Vivado infer true block RAM primitives.
    // -----------------------------------------------------------------------
    (* ram_style = "block" *) reg signed [31:0] lp_bank0 [0:255];
    (* ram_style = "block" *) reg signed [31:0] lp_bank1 [0:255];
    (* ram_style = "block" *) reg signed [31:0] lp_bank2 [0:255];
    (* ram_style = "block" *) reg signed [31:0] lp_bank3 [0:255];

    reg signed [31:0] bank_rd_data [0:3];

    // Latched step configuration registers
    reg [1:0]         state;
    reg [9:0]         phase_cnt;
    reg [15:0]        total_cyc;
    reg signed [31:0] r_f_init_hz;
    reg signed [31:0] r_f_probe_hz;
    reg signed [31:0] r_y_meas_q16;
    reg        [31:0] r_inv_gamma_q24;
    reg signed [31:0] r_inv_2var_q16;
    reg        [15:0] r_delta_fisher_q4;
    reg        [15:0] r_max_off_q4;
    reg        [7:0]  r_step_idx;

    assign busy = (state != S_IDLE);

    // Sweep issue control
    wire       p1_issue = (state == S_PASS1) && (phase_cnt < SWEEP_BEATS_U10);
    wire       p2_issue = (state == S_PASS2) && (phase_cnt < SWEEP_BEATS_U10);
    wire [7:0] beat_idx = (phase_cnt < SWEEP_BEATS_U10) ? phase_cnt[7:0] : 8'd0;

    // Pass-1 pipeline registers (6-stage cleanly pipelined datapath, aligned to 2-cycle LOR LUT)
    reg [7:0]         p1_addr_d1, p1_addr_d2, p1_addr_d3, p1_addr_d4, p1_addr_d5, p1_addr_d6;
    reg [3:0]         p1_act_d1,  p1_act_d2,  p1_act_d3,  p1_act_d4,  p1_act_d5,  p1_act_d6;
    reg signed [31:0] p1_old_lp_d2 [0:3];
    reg signed [31:0] p1_old_lp_d3 [0:3];
    reg signed [31:0] p1_old_lp_d4 [0:3];
    reg signed [31:0] p1_old_lp_d5 [0:3];
    reg signed [31:0] p1_res_d3    [0:3];
    reg signed [31:0] p1_resid2_d4 [0:3];
    reg signed [31:0] p1_dlp_d5    [0:3];
    reg signed [31:0] p1_new_lp_d6 [0:3];

    // Pass-2 pipeline registers (exact 1-cycle BRAM read alignment + pipelined MAC)
    reg               p2_rd_valid;
    reg [7:0]         p2_rd_beat_idx;
    reg [3:0]         p2_rd_act;

    reg               p2_s2_valid;
    reg [7:0]         p2_s2_beat;
    reg [3:0]         p2_s2_act;
    reg signed [31:0] p2_neg_x_s2 [0:3];

    reg               p2_s3_valid;
    reg [7:0]         p2_s3_beat;
    reg [3:0]         p2_s3_act;

    reg               p2_s4_valid;
    reg [3:0]         p2_s4_act;
    reg signed [15:0] p2_df_s4  [0:3];
    reg signed [19:0] p2_df2_s4 [0:3];

    reg               p2_s5_valid;
    reg signed [47:0] p2_w_s5   [0:3];
    reg signed [47:0] p2_m1p_s5 [0:3];
    reg signed [47:0] p2_m2p_s5 [0:3];

    reg               p2_s6_valid;
    reg signed [47:0] p2_z_01_s6,  p2_z_23_s6;
    reg signed [47:0] p2_m1_01_s6, p2_m1_23_s6;
    reg signed [47:0] p2_m2_01_s6, p2_m2_23_s6;

    // Unified write port mux per bank (S_IDLE prior load OR S_PASS1 Stage-7 writeback)
    wire               bank_wr_en0   = ((state == S_IDLE) && prior_load_en && (prior_load_addr[1:0] == 2'd0)) ||
                                       ((state == S_PASS1) && p1_act_d6[0]);
    wire               bank_wr_en1   = ((state == S_IDLE) && prior_load_en && (prior_load_addr[1:0] == 2'd1)) ||
                                       ((state == S_PASS1) && p1_act_d6[1]);
    wire               bank_wr_en2   = ((state == S_IDLE) && prior_load_en && (prior_load_addr[1:0] == 2'd2)) ||
                                       ((state == S_PASS1) && p1_act_d6[2]);
    wire               bank_wr_en3   = ((state == S_IDLE) && prior_load_en && (prior_load_addr[1:0] == 2'd3)) ||
                                       ((state == S_PASS1) && p1_act_d6[3]);
    wire        [7:0]  bank_wr_addr  = (state == S_IDLE) ? prior_load_addr[9:2] : p1_addr_d6;
    wire signed [31:0] bank_wr_data0 = (state == S_IDLE) ? prior_load_lp_q16 : p1_new_lp_d6[0];
    wire signed [31:0] bank_wr_data1 = (state == S_IDLE) ? prior_load_lp_q16 : p1_new_lp_d6[1];
    wire signed [31:0] bank_wr_data2 = (state == S_IDLE) ? prior_load_lp_q16 : p1_new_lp_d6[2];
    wire signed [31:0] bank_wr_data3 = (state == S_IDLE) ? prior_load_lp_q16 : p1_new_lp_d6[3];

    always @(posedge clk) begin
        if (bank_wr_en0) lp_bank0[bank_wr_addr] <= bank_wr_data0;
        if (bank_wr_en1) lp_bank1[bank_wr_addr] <= bank_wr_data1;
        if (bank_wr_en2) lp_bank2[bank_wr_addr] <= bank_wr_data2;
        if (bank_wr_en3) lp_bank3[bank_wr_addr] <= bank_wr_data3;
        bank_rd_data[0] <= lp_bank0[beat_idx];
        bank_rd_data[1] <= lp_bank1[beat_idx];
        bank_rd_data[2] <= lp_bank2[beat_idx];
        bank_rd_data[3] <= lp_bank3[beat_idx];
    end

    // -----------------------------------------------------------------------
    // 3. 4 Parallel SIMD Lanes: Lorentzian LUT (Pass 1) & exp(-x) LUT (Pass 2)
    // -----------------------------------------------------------------------
    wire signed [31:0] lor_x_in    [0:3];
    wire               lor_v_out   [0:3];
    wire signed [31:0] lor_y_out   [0:3];

    wire               exp_v_out   [0:3];
    wire signed [31:0] exp_y_out   [0:3];

    // Per-lane combinational Pass-1 Q16.16 products & saturated updates (zero static function calls!)
    wire signed [31:0] p1_r2_next  [0:3];
    wire signed [31:0] p1_dlp_next [0:3];
    wire signed [31:0] p1_sat_next [0:3];

    // Per-lane combinational Pass-2 saturated neg_x, df, df^2, and DSP48E2 products
    wire signed [31:0] p2_negx_c   [0:3];
    wire signed [15:0] p2_df_s3_c  [0:3];
    wire signed [19:0] p2_df2_s3_c [0:3];
    wire signed [47:0] p2_m1_prod  [0:3];
    wire signed [47:0] p2_m2_prod  [0:3];

    wire [3:0]         beat_active_mask;
    wire [3:0]         lane_unused_bits;

    reg  signed [31:0] max_lp_reg;

    // 48-bit signed DSP48E2 moment accumulators (zero overflow for N=1001, df in [-500..+500])
    reg  signed [47:0] acc_z;
    reg  signed [47:0] acc_m1;
    reg  signed [47:0] acc_m2;

    genvar ln;
    generate
        for (ln = 0; ln < 4; ln = ln + 1) begin : gen_simd_lane
            wire [10:0]        bin_linear = ({3'd0, beat_idx} << 2) + ln[10:0];
            wire               bin_active = (bin_linear < N_FINE_BINS_U11);
            assign beat_active_mask[ln]   = bin_active;

            wire signed [15:0] df_bin     = $signed({5'd0, bin_linear}) - 16'sd500;
            wire signed [31:0] grid_hz_l  = r_f_init_hz + ({{16{df_bin[15]}}, df_bin} * BIN_STEP_S32);
            wire signed [31:0] diff_hz_l  = r_f_probe_hz - grid_hz_l;
            wire        [31:0] abs_df_l   = diff_hz_l[31] ? (-diff_hz_l) : diff_hz_l;
            wire        [63:0] u_prod_l   = ({32'd0, abs_df_l} * {32'd0, r_inv_gamma_q24}) + 64'd128;
            assign lor_x_in[ln]           = {1'b0, u_prod_l[38:8]};

            boed_lut_rom #(
                .MEM_FILE  (LOR_HEX_FILE),
                .SCALE_ADDR(32'd10923),
                .GUARD_WORD(32'h000001C4),
                .TAIL_WORD (32'h000001C4)
            ) u_lor_lut (
                .clk      (clk),
                .rst_n    (rst_n),
                .in_valid (p1_issue && bin_active),
                .x_q16    (lor_x_in[ln]),
                .out_valid(lor_v_out[ln]),
                .y_q16    (lor_y_out[ln])
            );

            // Pass-1 Stage 4: resid^2 in Q16.16 (registered p1_res_d3 -> p1_resid2_d4)
            wire signed [63:0] r2_prod_l  = ({{32{p1_res_d3[ln][31]}}, p1_res_d3[ln]} *
                                             {{32{p1_res_d3[ln][31]}}, p1_res_d3[ln]}) + 64'sd32768;
            assign p1_r2_next[ln]         = $signed(r2_prod_l[47:16]);

            // Pass-1 Stage 5: resid^2 * inv_2var in Q16.16 (registered p1_resid2_d4 -> p1_dlp_d5)
            wire signed [63:0] dlp_prod_l = ({{32{p1_resid2_d4[ln][31]}}, p1_resid2_d4[ln]} *
                                             {{32{r_inv_2var_q16[31]}}, r_inv_2var_q16}) + 64'sd32768;
            assign p1_dlp_next[ln]        = $signed(dlp_prod_l[47:16]);

            // Pass-1 Stage 6: saturated 32-bit signed subtraction old_lp - dlp
            wire signed [32:0] sub_lp_l   = $signed({p1_old_lp_d5[ln][31], p1_old_lp_d5[ln]}) -
                                            $signed({p1_dlp_d5[ln][31], p1_dlp_d5[ln]});
            assign p1_sat_next[ln]        = (sub_lp_l > $signed({1'b0, INT32_MAX_VAL})) ? INT32_MAX_VAL :
                                            (sub_lp_l < $signed({1'b1, INT32_MIN_VAL})) ? INT32_MIN_VAL :
                                            $signed(sub_lp_l[31:0]);

            // Pass-2 Stage 2: 33-bit overflow-safe non-negative diff (max_lp_reg - bank_rd_data[ln])
            // Prevents 32-bit wrap to negative when lp saturated to INT32_MIN!
            wire signed [32:0] diff_lp_l  = $signed({max_lp_reg[31], max_lp_reg}) -
                                            $signed({bank_rd_data[ln][31], bank_rd_data[ln]});
            assign p2_negx_c[ln]          = diff_lp_l[32] ? 32'sd0 :
                                            (diff_lp_l > $signed({1'b0, INT32_MAX_VAL})) ? INT32_MAX_VAL :
                                            $signed(diff_lp_l[31:0]);

            // Pass-2 Stage 3-4: 2-cycle BRAM exp(-x) LUT aligned 1:1 with p2_s2_valid & p2_s2_beat
            boed_lut_rom #(
                .MEM_FILE  (EXP_HEX_FILE),
                .SCALE_ADDR(32'd8192),
                .GUARD_WORD(32'h00000000),
                .TAIL_WORD (32'h00000000)
            ) u_exp_lut (
                .clk      (clk),
                .rst_n    (rst_n),
                .in_valid (p2_s2_valid && p2_s2_act[ln]),
                .x_q16    (p2_neg_x_s2[ln]),
                .out_valid(exp_v_out[ln]),
                .y_q16    (exp_y_out[ln])
            );

            // Pass-2 Stage 4: pre-compute df and df^2 in parallel with exp LUT interpolation
            wire [10:0]        p2_bin_s3  = ({3'd0, p2_s3_beat} << 2) + ln[10:0];
            assign p2_df_s3_c[ln]         = $signed({5'd0, p2_bin_s3}) - 16'sd500;
            wire signed [31:0] df2_s3_w   = {{16{p2_df_s3_c[ln][15]}}, p2_df_s3_c[ln]} *
                                            {{16{p2_df_s3_c[ln][15]}}, p2_df_s3_c[ln]};
            assign p2_df2_s3_c[ln]        = $signed(df2_s3_w[19:0]);

            // Pass-2 Stage 5: Single-DSP48E2 products (exp_y_out in [0..65536] fits in 18b signed!)
            wire signed [24:0] w_s25      = $signed(exp_y_out[ln][24:0]);
            wire signed [17:0] w_s18      = $signed(exp_y_out[ln][17:0]);
            wire signed [40:0] m1_p41     = {{16{w_s25[24]}}, w_s25} * {{25{p2_df_s4[ln][15]}}, p2_df_s4[ln]};
            wire signed [37:0] m2_p38     = {{18{p2_df2_s4[ln][19]}}, p2_df2_s4[ln]} * {{20{w_s18[17]}}, w_s18};
            assign p2_m1_prod[ln]         = {{7{m1_p41[40]}}, m1_p41};
            assign p2_m2_prod[ln]         = {{10{m2_p38[37]}}, m2_p38};

            assign lane_unused_bits[ln]   = &{1'b0, lor_v_out[ln], exp_v_out[ln],
                                              u_prod_l[63:39], u_prod_l[7:0],
                                              r2_prod_l[63:48], r2_prod_l[15:0],
                                              dlp_prod_l[63:48], dlp_prod_l[15:0],
                                              df2_s3_w[31:20], exp_y_out[ln][31:25]};
        end
    endgenerate

    // Bug 1 Fix: Clean combinational 4-way comparator tree for running max_lp_reg
    wire signed [31:0] p1_cand0   = p1_act_d6[0] ? p1_new_lp_d6[0] : INT32_MIN_VAL;
    wire signed [31:0] p1_cand1   = p1_act_d6[1] ? p1_new_lp_d6[1] : INT32_MIN_VAL;
    wire signed [31:0] p1_cand2   = p1_act_d6[2] ? p1_new_lp_d6[2] : INT32_MIN_VAL;
    wire signed [31:0] p1_cand3   = p1_act_d6[3] ? p1_new_lp_d6[3] : INT32_MIN_VAL;
    wire signed [31:0] lane01_max = (p1_cand0 > p1_cand1) ? p1_cand0 : p1_cand1;
    wire signed [31:0] lane23_max = (p1_cand2 > p1_cand3) ? p1_cand2 : p1_cand3;
    wire signed [31:0] beat_max   = (lane01_max > lane23_max) ? lane01_max : lane23_max;

    // -----------------------------------------------------------------------
    // 4. Stage-3 Post-Processing: 3 Parallel Bit-Serial Restoring Dividers
    //    (ZERO `/` operators!) + 16-Stage Pipelined Restoring isqrt
    // -----------------------------------------------------------------------
    reg               isqrt_in_v;
    reg        [31:0] isqrt_rad_in;
    wire              isqrt_out_v;
    wire       [15:0] isqrt_root_out;

    boed_isqrt_cordic u_isqrt (
        .clk      (clk),
        .rst_n    (rst_n),
        .in_valid (isqrt_in_v),
        .radicand (isqrt_rad_in),
        .out_valid(isqrt_out_v),
        .root     (isqrt_root_out)
    );

    // Restoring integer divider registers:
    //   div1: |acc_m1| * 256  / acc_z  (K1 = 18 bits, cycles 1..18)
    //   div2: |acc_m1| * 2560 / acc_z  (K2 = 21 bits, cycles 1..21)
    //   div3: (acc_m2 << 16)  / acc_z  (K3 = 35 bits, cycles 1..35)
    reg        [47:0] div_den;
    reg               div_m1_neg;

    reg        [47:0] div1_rem;
    reg        [17:0] div1_shreg;
    reg        [17:0] div1_quot;

    reg        [47:0] div2_rem;
    reg        [20:0] div2_shreg;
    reg        [20:0] div2_quot;

    reg        [47:0] div3_rem;
    reg        [34:0] div3_shreg;
    reg        [34:0] div3_quot;

    reg        [17:0] post_mean_b_abs;
    reg        [35:0] post_mean_b_sq;
    reg signed [31:0] post_mu_off_q8;
    reg        [35:0] post_var_bins_q16;

    // Divider initialization combinational prep (phase_cnt == 0 in S_POST)
    wire              z_pos_ok   = (acc_z > 48'sd0);
    wire       [47:0] den_init   = z_pos_ok ? acc_z[47:0] : 48'd1;
    wire              m1_neg_c   = z_pos_ok && acc_m1[47];
    wire       [47:0] abs_m1_c   = (!z_pos_ok) ? 48'd0 : (acc_m1[47] ? (-acc_m1[47:0]) : acc_m1[47:0]);
    wire       [43:0] num1_init  = {abs_m1_c[35:0], 8'd0};
    wire       [47:0] num2_init  = {1'b0, abs_m1_c[35:0], 11'd0} + {3'd0, abs_m1_c[35:0], 9'd0}; // * 2560
    wire       [59:0] num3_init  = z_pos_ok ? {acc_m2[43:0], 16'd0} : 60'd0;

    // Single-cycle restoring shift-subtract steps (1 bit per cycle per divider)
    wire       [47:0] d1_rem_next = {div1_rem[46:0], div1_shreg[17]};
    wire              d1_ge       = (d1_rem_next >= div_den);

    wire       [47:0] d2_rem_next = {div2_rem[46:0], div2_shreg[20]};
    wire              d2_ge       = (d2_rem_next >= div_den);

    wire       [47:0] d3_rem_next = {div3_rem[46:0], div3_shreg[34]};
    wire              d3_ge       = (d3_rem_next >= div_den);

    // Exact signed floor quotient adjustments (matches Python // bit-for-bit!)
    wire       [17:0] mb_abs_adj  = (div_m1_neg && (div1_rem != 48'd0)) ? (div1_quot + 18'd1) : div1_quot;
    wire       [31:0] mu_mag_adj  = (div_m1_neg && (div2_rem != 48'd0)) ? ({11'd0, div2_quot} + 32'd1) : {11'd0, div2_quot};
    wire signed [31:0] mu_floor_c = div_m1_neg ? (-$signed(mu_mag_adj)) : $signed(mu_mag_adj);

    // Exact 44-bit unsigned variance scaling: (var_bins_q16 * 100) >> 8 using shift-add (64+32+4=100)
    wire       [43:0] var_x100_c  = {2'd0, post_var_bins_q16, 6'd0} +
                                    {3'd0, post_var_bins_q16, 5'd0} +
                                    {6'd0, post_var_bins_q16, 2'd0};
    wire       [35:0] var_hz2_c   = var_x100_c[43:8];
    wire       [31:0] var_sat_u32 = (|var_hz2_c[35:32]) ? 32'hFFFFFFFF : var_hz2_c[31:0];

    // Fisher inflection offset combinational helper
    wire [23:0] std_scaled_full = ({8'd0, isqrt_root_out} * 24'd282) >> 8;
    wire [15:0] std_scaled_q4   = std_scaled_full[15:0];
    wire [15:0] min_std_max     = (std_scaled_q4 < r_max_off_q4) ? std_scaled_q4 : r_max_off_q4;
    wire [15:0] fisher_off_q4   = (r_delta_fisher_q4 > min_std_max) ? r_delta_fisher_q4 : min_std_max;
    wire        next_sign_neg   = r_step_idx[0];  // (step_idx + 1) % 2 == 0 <-> step_idx odd -> -1

    wire _unused_ok = &{1'b0, SIMD_LANES[0], r_step_idx[7:1], lane_unused_bits,
                        sprt_round_s2[63:48], sprt_round_s2[15:0],
                        abs_m1_c[47:36], acc_m2[47:44],
                        div1_rem[47], div2_rem[47], div3_rem[47],
                        var_x100_c[7:0], std_scaled_full[23:16]};

    // -----------------------------------------------------------------------
    // 5. Main Deterministic 584-Cycle Control FSM & Datapath
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n) begin
            state             <= S_IDLE;
            phase_cnt         <= 10'd0;
            total_cyc         <= 16'd0;
            cycle_count       <= 16'd0;
            step_done         <= 1'b0;
            mu_off_q8         <= 32'sd0;
            std_q4            <= 16'd0;
            next_probe_off_q8 <= 32'sd0;
            r_f_init_hz       <= 32'sd0;
            r_f_probe_hz      <= 32'sd0;
            r_y_meas_q16      <= 32'sd0;
            r_inv_gamma_q24   <= 32'd0;
            r_inv_2var_q16    <= 32'sd0;
            r_delta_fisher_q4 <= 16'd0;
            r_max_off_q4      <= 16'd0;
            r_step_idx        <= 8'd0;
            max_lp_reg        <= INT32_MIN_VAL;
            acc_z             <= 48'sd0;
            acc_m1            <= 48'sd0;
            acc_m2            <= 48'sd0;
            p1_act_d1         <= 4'd0;
            p1_act_d2         <= 4'd0;
            p1_act_d3         <= 4'd0;
            p1_act_d4         <= 4'd0;
            p1_act_d5         <= 4'd0;
            p1_act_d6         <= 4'd0;
            p1_addr_d1        <= 8'd0;
            p1_addr_d2        <= 8'd0;
            p1_addr_d3        <= 8'd0;
            p1_addr_d4        <= 8'd0;
            p1_addr_d5        <= 8'd0;
            p1_addr_d6        <= 8'd0;
            p2_rd_valid       <= 1'b0;
            p2_rd_beat_idx    <= 8'd0;
            p2_rd_act         <= 4'd0;
            p2_s2_valid       <= 1'b0;
            p2_s2_beat        <= 8'd0;
            p2_s2_act         <= 4'd0;
            p2_s3_valid       <= 1'b0;
            p2_s3_beat        <= 8'd0;
            p2_s3_act         <= 4'd0;
            p2_s4_valid       <= 1'b0;
            p2_s4_act         <= 4'd0;
            p2_s5_valid       <= 1'b0;
            p2_s6_valid       <= 1'b0;
            p2_z_01_s6        <= 48'sd0;
            p2_z_23_s6        <= 48'sd0;
            p2_m1_01_s6       <= 48'sd0;
            p2_m1_23_s6       <= 48'sd0;
            p2_m2_01_s6       <= 48'sd0;
            p2_m2_23_s6       <= 48'sd0;
            isqrt_in_v        <= 1'b0;
            isqrt_rad_in      <= 32'd0;
            div_den           <= 48'd1;
            div_m1_neg        <= 1'b0;
            div1_rem          <= 48'd0;
            div1_shreg        <= 18'd0;
            div1_quot         <= 18'd0;
            div2_rem          <= 48'd0;
            div2_shreg        <= 21'd0;
            div2_quot         <= 21'd0;
            div3_rem          <= 48'd0;
            div3_shreg        <= 35'd0;
            div3_quot         <= 35'd0;
            post_mean_b_abs   <= 18'd0;
            post_mean_b_sq    <= 36'd0;
            post_mu_off_q8    <= 32'sd0;
            post_var_bins_q16 <= 36'd0;
        end else begin
            step_done  <= 1'b0;
            isqrt_in_v <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (step_start) begin
                        r_f_init_hz       <= f_init_hz;
                        r_f_probe_hz      <= f_probe_hz;
                        r_y_meas_q16      <= y_meas_q16;
                        r_inv_gamma_q24   <= inv_gamma_q24;
                        r_inv_2var_q16    <= inv_2var_q16;
                        r_delta_fisher_q4 <= delta_fisher_q4;
                        r_max_off_q4      <= max_off_q4;
                        r_step_idx        <= step_idx;
                        max_lp_reg        <= INT32_MIN_VAL;
                        acc_z             <= 48'sd0;
                        acc_m1            <= 48'sd0;
                        acc_m2            <= 48'sd0;
                        p1_act_d1         <= 4'd0;
                        p1_act_d2         <= 4'd0;
                        p1_act_d3         <= 4'd0;
                        p1_act_d4         <= 4'd0;
                        p1_act_d5         <= 4'd0;
                        p1_act_d6         <= 4'd0;
                        p2_rd_valid       <= 1'b0;
                        p2_rd_act         <= 4'd0;
                        p2_s2_valid       <= 1'b0;
                        p2_s2_act         <= 4'd0;
                        p2_s3_valid       <= 1'b0;
                        p2_s3_act         <= 4'd0;
                        p2_s4_valid       <= 1'b0;
                        p2_s4_act         <= 4'd0;
                        p2_s5_valid       <= 1'b0;
                        p2_s6_valid       <= 1'b0;
                        phase_cnt         <= 10'd0;
                        total_cyc         <= 16'd0;
                        state             <= S_PASS1;
                    end
                end

                // Pass 1: 263 deterministic clock cycles (251 beats + 12 drain cycles)
                S_PASS1: begin
                    total_cyc <= total_cyc + 16'd1;

                    // Stage 1: BRAM read issued in parallel with u_lor_lut Stage 1
                    p1_addr_d1 <= beat_idx;
                    p1_act_d1  <= p1_issue ? beat_active_mask : 4'd0;

                    // Stage 2: align BRAM read output with 2-cycle Lorentzian LUT output
                    p1_addr_d2      <= p1_addr_d1;
                    p1_act_d2       <= p1_act_d1;
                    p1_old_lp_d2[0] <= bank_rd_data[0];
                    p1_old_lp_d2[1] <= bank_rd_data[1];
                    p1_old_lp_d2[2] <= bank_rd_data[2];
                    p1_old_lp_d2[3] <= bank_rd_data[3];

                    // Stage 3: residual = y_meas - lor_y_out
                    p1_addr_d3      <= p1_addr_d2;
                    p1_act_d3       <= p1_act_d2;
                    p1_old_lp_d3[0] <= p1_old_lp_d2[0];
                    p1_old_lp_d3[1] <= p1_old_lp_d2[1];
                    p1_old_lp_d3[2] <= p1_old_lp_d2[2];
                    p1_old_lp_d3[3] <= p1_old_lp_d2[3];
                    p1_res_d3[0]    <= r_y_meas_q16 - lor_y_out[0];
                    p1_res_d3[1]    <= r_y_meas_q16 - lor_y_out[1];
                    p1_res_d3[2]    <= r_y_meas_q16 - lor_y_out[2];
                    p1_res_d3[3]    <= r_y_meas_q16 - lor_y_out[3];

                    // Stage 4: residual^2 in Q16.16
                    p1_addr_d4      <= p1_addr_d3;
                    p1_act_d4       <= p1_act_d3;
                    p1_old_lp_d4[0] <= p1_old_lp_d3[0];
                    p1_old_lp_d4[1] <= p1_old_lp_d3[1];
                    p1_old_lp_d4[2] <= p1_old_lp_d3[2];
                    p1_old_lp_d4[3] <= p1_old_lp_d3[3];
                    p1_resid2_d4[0] <= p1_r2_next[0];
                    p1_resid2_d4[1] <= p1_r2_next[1];
                    p1_resid2_d4[2] <= p1_r2_next[2];
                    p1_resid2_d4[3] <= p1_r2_next[3];

                    // Stage 5: delta_lp = residual^2 * inv_2var in Q16.16
                    p1_addr_d5      <= p1_addr_d4;
                    p1_act_d5       <= p1_act_d4;
                    p1_old_lp_d5[0] <= p1_old_lp_d4[0];
                    p1_old_lp_d5[1] <= p1_old_lp_d4[1];
                    p1_old_lp_d5[2] <= p1_old_lp_d4[2];
                    p1_old_lp_d5[3] <= p1_old_lp_d4[3];
                    p1_dlp_d5[0]    <= p1_dlp_next[0];
                    p1_dlp_d5[1]    <= p1_dlp_next[1];
                    p1_dlp_d5[2]    <= p1_dlp_next[2];
                    p1_dlp_d5[3]    <= p1_dlp_next[3];

                    // Stage 6: saturated log-posterior update
                    p1_addr_d6      <= p1_addr_d5;
                    p1_act_d6       <= p1_act_d5;
                    p1_new_lp_d6[0] <= p1_sat_next[0];
                    p1_new_lp_d6[1] <= p1_sat_next[1];
                    p1_new_lp_d6[2] <= p1_sat_next[2];
                    p1_new_lp_d6[3] <= p1_sat_next[3];

                    // Stage 7: BRAM writeback (in BRAM block above) + single-assignment comparator tree max_lp_reg
                    if (|p1_act_d6) begin
                        if (beat_max > max_lp_reg) begin
                            max_lp_reg <= beat_max;
                        end
                    end

                    if (phase_cnt == PASS1_LIMIT - 10'd1) begin
                        phase_cnt   <= 10'd0;
                        p2_rd_valid <= 1'b0;
                        p2_rd_act   <= 4'd0;
                        p2_s2_valid <= 1'b0;
                        p2_s2_act   <= 4'd0;
                        p2_s3_valid <= 1'b0;
                        p2_s3_act   <= 4'd0;
                        p2_s4_valid <= 1'b0;
                        p2_s4_act   <= 4'd0;
                        p2_s5_valid <= 1'b0;
                        p2_s6_valid <= 1'b0;
                        state       <= S_PASS2;
                    end else begin
                        phase_cnt <= phase_cnt + 10'd1;
                    end
                end

                // Pass 2: 265 deterministic clock cycles (1:1 BRAM aligned exp LUT + pipelined 48b MAC)
                S_PASS2: begin
                    total_cyc <= total_cyc + 16'd1;

                    // Stage 1: BRAM read issued on beat_idx -> bank_rd_data valid on next cycle
                    p2_rd_valid    <= p2_issue;
                    p2_rd_beat_idx <= beat_idx;
                    p2_rd_act      <= p2_issue ? beat_active_mask : 4'd0;

                    // Stage 2: overflow-safe neg_x = sat(max_lp_reg - bank_rd_data) -> drives u_exp_lut
                    p2_s2_valid    <= p2_rd_valid;
                    p2_s2_beat     <= p2_rd_beat_idx;
                    p2_s2_act      <= p2_rd_act;
                    p2_neg_x_s2[0] <= p2_negx_c[0];
                    p2_neg_x_s2[1] <= p2_negx_c[1];
                    p2_neg_x_s2[2] <= p2_negx_c[2];
                    p2_neg_x_s2[3] <= p2_negx_c[3];

                    // Stage 3: aligned with u_exp_lut Stage 1 BRAM read
                    p2_s3_valid <= p2_s2_valid;
                    p2_s3_beat  <= p2_s2_beat;
                    p2_s3_act   <= p2_s2_act;

                    // Stage 4: aligned with u_exp_lut Stage 2 output (exp_y_out valid) + pre-registered df & df^2
                    p2_s4_valid  <= p2_s3_valid;
                    p2_s4_act    <= p2_s3_act;
                    p2_df_s4[0]  <= p2_df_s3_c[0];
                    p2_df_s4[1]  <= p2_df_s3_c[1];
                    p2_df_s4[2]  <= p2_df_s3_c[2];
                    p2_df_s4[3]  <= p2_df_s3_c[3];
                    p2_df2_s4[0] <= p2_df2_s3_c[0];
                    p2_df2_s4[1] <= p2_df2_s3_c[1];
                    p2_df2_s4[2] <= p2_df2_s3_c[2];
                    p2_df2_s4[3] <= p2_df2_s3_c[3];

                    // Stage 5: registered DSP48E2 products (w, w*df, w*df^2)
                    p2_s5_valid  <= p2_s4_valid;
                    p2_w_s5[0]   <= p2_s4_act[0] ? {{16{exp_y_out[0][31]}}, exp_y_out[0]} : 48'sd0;
                    p2_w_s5[1]   <= p2_s4_act[1] ? {{16{exp_y_out[1][31]}}, exp_y_out[1]} : 48'sd0;
                    p2_w_s5[2]   <= p2_s4_act[2] ? {{16{exp_y_out[2][31]}}, exp_y_out[2]} : 48'sd0;
                    p2_w_s5[3]   <= p2_s4_act[3] ? {{16{exp_y_out[3][31]}}, exp_y_out[3]} : 48'sd0;
                    p2_m1p_s5[0] <= p2_s4_act[0] ? p2_m1_prod[0] : 48'sd0;
                    p2_m1p_s5[1] <= p2_s4_act[1] ? p2_m1_prod[1] : 48'sd0;
                    p2_m1p_s5[2] <= p2_s4_act[2] ? p2_m1_prod[2] : 48'sd0;
                    p2_m1p_s5[3] <= p2_s4_act[3] ? p2_m1_prod[3] : 48'sd0;
                    p2_m2p_s5[0] <= p2_s4_act[0] ? p2_m2_prod[0] : 48'sd0;
                    p2_m2p_s5[1] <= p2_s4_act[1] ? p2_m2_prod[1] : 48'sd0;
                    p2_m2p_s5[2] <= p2_s4_act[2] ? p2_m2_prod[2] : 48'sd0;
                    p2_m2p_s5[3] <= p2_s4_act[3] ? p2_m2_prod[3] : 48'sd0;

                    // Stage 6: pairwise 48-bit adder tree
                    p2_s6_valid <= p2_s5_valid;
                    p2_z_01_s6  <= p2_w_s5[0]   + p2_w_s5[1];
                    p2_z_23_s6  <= p2_w_s5[2]   + p2_w_s5[3];
                    p2_m1_01_s6 <= p2_m1p_s5[0] + p2_m1p_s5[1];
                    p2_m1_23_s6 <= p2_m1p_s5[2] + p2_m1p_s5[3];
                    p2_m2_01_s6 <= p2_m2p_s5[0] + p2_m2p_s5[1];
                    p2_m2_23_s6 <= p2_m2p_s5[2] + p2_m2p_s5[3];

                    // Stage 7: final 48-bit moment accumulation
                    if (p2_s6_valid) begin
                        acc_z  <= acc_z  + p2_z_01_s6  + p2_z_23_s6;
                        acc_m1 <= acc_m1 + p2_m1_01_s6 + p2_m1_23_s6;
                        acc_m2 <= acc_m2 + p2_m2_01_s6 + p2_m2_23_s6;
                    end

                    if (phase_cnt == PASS2_LIMIT - 10'd1) begin
                        phase_cnt <= 10'd0;
                        state     <= S_POST;
                    end else begin
                        phase_cnt <= phase_cnt + 10'd1;
                    end
                end

                // Pass 3: 56 deterministic clock cycles (3 parallel restoring dividers + 16-stage isqrt + Fisher)
                S_POST: begin
                    total_cyc <= total_cyc + 16'd1;

                    // Cycle 0: Initialize all 3 parallel bit-serial restoring dividers
                    if (phase_cnt == 10'd0) begin
                        div_den    <= den_init;
                        div_m1_neg <= m1_neg_c;

                        div1_rem   <= {22'd0, num1_init[43:18]};
                        div1_shreg <= num1_init[17:0];
                        div1_quot  <= 18'd0;

                        div2_rem   <= {21'd0, num2_init[47:21]};
                        div2_shreg <= num2_init[20:0];
                        div2_quot  <= 21'd0;

                        div3_rem   <= {23'd0, num3_init[59:35]};
                        div3_shreg <= num3_init[34:0];
                        div3_quot  <= 35'd0;
                    end

                    // Cycles 1..18: Restoring shift-subtract Divider 1 (mean_b_q8)
                    if ((phase_cnt >= 10'd1) && (phase_cnt <= 10'd18)) begin
                        div1_rem   <= d1_ge ? (d1_rem_next - div_den) : d1_rem_next;
                        div1_quot  <= {div1_quot[16:0], d1_ge};
                        div1_shreg <= {div1_shreg[16:0], 1'b0};
                    end

                    // Cycles 1..21: Restoring shift-subtract Divider 2 (mu_off_q8)
                    if ((phase_cnt >= 10'd1) && (phase_cnt <= 10'd21)) begin
                        div2_rem   <= d2_ge ? (d2_rem_next - div_den) : d2_rem_next;
                        div2_quot  <= {div2_quot[19:0], d2_ge};
                        div2_shreg <= {div2_shreg[19:0], 1'b0};
                    end

                    // Cycles 1..35: Restoring shift-subtract Divider 3 (ex2_q16)
                    if ((phase_cnt >= 10'd1) && (phase_cnt <= 10'd35)) begin
                        div3_rem   <= d3_ge ? (d3_rem_next - div_den) : d3_rem_next;
                        div3_quot  <= {div3_quot[33:0], d3_ge};
                        div3_shreg <= {div3_shreg[33:0], 1'b0};
                    end

                    // Cycle 19: Latch floor-adjusted |mean_b_q8| (18-bit unsigned)
                    if (phase_cnt == 10'd19) begin
                        post_mean_b_abs <= mb_abs_adj;
                    end

                    // Cycle 20: Exact 36-bit unsigned square mean_b_q8^2 (1 DSP48E2, zero overflow)
                    if (phase_cnt == 10'd20) begin
                        post_mean_b_sq <= {18'd0, post_mean_b_abs} * {18'd0, post_mean_b_abs};
                    end

                    // Cycle 22: Latch exact floor-divided mu_off_q8
                    if (phase_cnt == 10'd22) begin
                        post_mu_off_q8 <= mu_floor_c;
                    end

                    // Cycle 36: Exact 36-bit unsigned variance in bins (ex2_q16 - mean_b_q8^2)
                    if (phase_cnt == 10'd36) begin
                        if ({1'b0, div3_quot} > post_mean_b_sq) begin
                            post_var_bins_q16 <= {1'b0, div3_quot} - post_mean_b_sq;
                        end else begin
                            post_var_bins_q16 <= 36'd0;
                        end
                    end

                    // Cycle 37: Scale to Hz^2 Q8 via exact shift-add (*100 >> 8) and launch 16-stage isqrt
                    if (phase_cnt == 10'd37) begin
                        isqrt_in_v   <= 1'b1;
                        isqrt_rad_in <= var_sat_u32;
                    end

                    // Cycle 54: Latch exact isqrt output and compute Fisher next-probe offset in Q8
                    if (isqrt_out_v) begin
                        mu_off_q8 <= post_mu_off_q8;
                        std_q4    <= isqrt_root_out;
                        if (next_sign_neg) begin
                            next_probe_off_q8 <= post_mu_off_q8 - $signed({12'd0, fisher_off_q4, 4'd0});
                        end else begin
                            next_probe_off_q8 <= post_mu_off_q8 + $signed({12'd0, fisher_off_q4, 4'd0});
                        end
                    end

                    // Cycle 55: Emit step_done with exact cycle_count == 584
                    if (phase_cnt == POST_LIMIT - 10'd1) begin
                        cycle_count <= total_cyc + 16'd1;
                        step_done   <= 1'b1;
                        phase_cnt   <= 10'd0;
                        state       <= S_IDLE;
                    end else begin
                        phase_cnt <= phase_cnt + 10'd1;
                    end
                end

                default: begin
                    state <= S_IDLE;
                end
            endcase
        end
    end
endmodule
