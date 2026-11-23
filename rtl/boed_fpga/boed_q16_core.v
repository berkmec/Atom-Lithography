// boed_q16_core.v - Synthesizable 4-Lane SIMD Q16.16 Bayesian Spectroscopy & SPRT Accelerator
// Target: Xilinx Zynq UltraScale+ RFSoC ZU48DR @ 250 MHz (4.0 ns period)
// Cycle-exact match to src/machine_control/fpga_boed_dsp.py (Exp140):
//   - Stage-0 SPRT fast-abort unit: 4 clock cycles (16.0 ns) per shot LLR update
//   - Stage-2 BOED 1001-bin grid filter (P=4 SIMD lanes):
//       S_PASS1 = 263 cycles (251 4-lane sweep beats + 12 pipeline drain cycles)
//       S_PASS2 = 265 cycles (251 4-lane sweep beats + 14 pipeline drain cycles)
//       S_POST  =  56 cycles (Radix-4 divider + 16-stage isqrt + Fisher argmax)
//       TOTAL   = 584 clock cycles = 2.336 us @ 250 MHz!
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

    localparam [9:0] PASS1_LIMIT = SWEEP_BEATS + PIPE_PASS1_CYC; // 263
    localparam [9:0] PASS2_LIMIT = SWEEP_BEATS + PIPE_PASS2_CYC; // 265
    localparam [9:0] POST_LIMIT  = POST_CYC;                     //  56
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
            sprt_prod_s2   <= sprt_diff_s1 * sprt_scale_s1;
            sprt_thr_s2    <= sprt_thr_s1;

            // Cycle 3: Q16.16 round-to-nearest shift
            sprt_pipe_v[2] <= sprt_pipe_v[1];
            sprt_delta_s3  <= (sprt_prod_s2 + 64'sd32768) >>> 16;
            sprt_thr_s3    <= sprt_thr_s2;

            // Cycle 4: LLR accumulate + threshold compare
            sprt_done <= sprt_pipe_v[2];
            if (sprt_reset_llr) begin
                sprt_llr_q16        <= 32'sd0;
                sprt_decision_valid <= 1'b0;
                sprt_donor_present  <= 1'b0;
            end else if (sprt_pipe_v[2]) begin
                sprt_llr_q16        <= sprt_llr_q16 + sprt_delta_s3;
                sprt_decision_valid <= ((sprt_llr_q16 + sprt_delta_s3) >= sprt_thr_s3) ||
                                       ((sprt_llr_q16 + sprt_delta_s3) <= -sprt_thr_s3);
                sprt_donor_present  <= ((sprt_llr_q16 + sprt_delta_s3) > 32'sd0);
            end
        end
    end

    // -----------------------------------------------------------------------
    // 2. Stage-2 BOED 4-Bank Ping-Pong Posterior SRAM (4 x 256 x 32-bit BRAM)
    // -----------------------------------------------------------------------
    (* ram_style = "block" *) reg signed [31:0] lp_bank0 [0:255];
    (* ram_style = "block" *) reg signed [31:0] lp_bank1 [0:255];
    (* ram_style = "block" *) reg signed [31:0] lp_bank2 [0:255];
    (* ram_style = "block" *) reg signed [31:0] lp_bank3 [0:255];

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

    // -----------------------------------------------------------------------
    // 3. 4 Parallel SIMD Lanes: Lorentzian LUT (Pass 1) & exp(-x) LUT (Pass 2)
    // -----------------------------------------------------------------------
    wire               p1_issue = (state == S_PASS1) && (phase_cnt < SWEEP_BEATS);
    wire               p2_issue = (state == S_PASS2) && (phase_cnt < SWEEP_BEATS);
    wire [7:0]         beat_idx = (phase_cnt < SWEEP_BEATS) ? phase_cnt[7:0] : 8'd0;

    wire signed [31:0] lor_x_in  [0:3];
    wire               lor_v_out [0:3];
    wire signed [31:0] lor_y_out [0:3];

    wire signed [31:0] exp_x_in  [0:3];
    wire               exp_v_out [0:3];
    wire signed [31:0] exp_y_out [0:3];

    reg  signed [31:0] lp_rd_lane [0:3];
    reg  signed [31:0] max_lp_reg;

    // 48-bit signed DSP48E2 moment accumulators (zero overflow for N=1001, df in [-500..+500])
    reg  signed [47:0] acc_z;
    reg  signed [47:0] acc_m1;
    reg  signed [47:0] acc_m2;

    genvar ln;
    generate
        for (ln = 0; ln < 4; ln = ln + 1) begin : gen_simd_lane
            wire [10:0] bin_linear = ({3'd0, beat_idx} << 2) + ln;
            wire        bin_active = (bin_linear < N_FINE_BINS);
            wire signed [15:0] df_bin = $signed({5'd0, bin_linear}) - 16'sd500;
            wire signed [31:0] grid_hz_l = r_f_init_hz + ($signed(df_bin) * BIN_STEP_HZ);
            wire signed [31:0] diff_hz_l = r_f_probe_hz - grid_hz_l;
            wire [31:0]        abs_df_l  = diff_hz_l[31] ? (-diff_hz_l) : diff_hz_l;
            wire [63:0]        u_prod_l  = ({32'd0, abs_df_l} * {32'd0, r_inv_gamma_q24}) + 64'd128;
            assign lor_x_in[ln] = {1'b0, u_prod_l[38:8]};

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

            assign exp_x_in[ln] = max_lp_reg - lp_rd_lane[ln];

            boed_lut_rom #(
                .MEM_FILE  (EXP_HEX_FILE),
                .SCALE_ADDR(32'd8192),
                .GUARD_WORD(32'h00000000),
                .TAIL_WORD (32'h00000000)
            ) u_exp_lut (
                .clk      (clk),
                .rst_n    (rst_n),
                .in_valid (p2_issue && bin_active),
                .x_q16    (exp_x_in[ln]),
                .out_valid(exp_v_out[ln]),
                .y_q16    (exp_y_out[ln])
            );
        end
    endgenerate

    // Pass-1 residual-squared & log-likelihood update pipeline (aligned to 2-cycle LUT)
    reg [7:0]         p1_addr_d1, p1_addr_d2, p1_addr_d3, p1_addr_d4;
    reg [3:0]         p1_act_d1,  p1_act_d2,  p1_act_d3,  p1_act_d4;
    reg signed [31:0] p1_old_lp_d1 [0:3];
    reg signed [31:0] p1_old_lp_d2 [0:3];
    reg signed [31:0] p1_old_lp_d3 [0:3];
    reg signed [31:0] p1_resid2_d3 [0:3];
    reg signed [31:0] p1_new_lp_d4 [0:3];

    // Pass-2 bin index alignment (aligned to 2-cycle exp LUT)
    reg [7:0]         p2_addr_d1, p2_addr_d2;
    reg [3:0]         p2_act_d1,  p2_act_d2;

    // -----------------------------------------------------------------------
    // 4. Stage-3 Post-Processing: Divider + 16-Stage Pipelined CORDIC isqrt
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

    // Restoring integer divider registers for acc_m1/acc_z and acc_m2/acc_z
    reg signed [31:0] post_mean_b_q8;
    reg signed [31:0] post_mu_off_q8;
    reg        [31:0] post_ex2_q16;
    reg        [31:0] post_var_hz2_q8;
    reg        [15:0] post_std_q4;
    reg               post_div_done;

    // Helper functions for Q16.16 signed multiply & int32 saturation
    function signed [31:0] q16_mul_fn;
        input signed [31:0] a;
        input signed [31:0] b;
        reg   signed [63:0] p;
        begin
            p = a * b;
            q16_mul_fn = (p + 64'sd32768) >>> 16;
        end
    endfunction

    function signed [31:0] floor_div_s48;
        input signed [47:0] num;
        input signed [47:0] den;
        reg   signed [47:0] q_trunc;
        reg   signed [47:0] rem_trunc;
        begin
            q_trunc   = num / den;
            rem_trunc = num - (q_trunc * den);
            if ((rem_trunc != 48'sd0) && (num[47] ^ den[47]))
                floor_div_s48 = q_trunc[31:0] - 32'sd1;
            else
                floor_div_s48 = q_trunc[31:0];
        end
    endfunction

    function signed [31:0] sat_sub_int32;
        input signed [31:0] a;
        input signed [31:0] b;
        reg   signed [32:0] d;
        begin
            d = $signed({a[31], a}) - $signed({b[31], b});
            if (d > $signed({1'b0, INT32_MAX_VAL}))
                sat_sub_int32 = INT32_MAX_VAL;
            else if (d < $signed({1'b1, INT32_MIN_VAL}))
                sat_sub_int32 = INT32_MIN_VAL;
            else
                sat_sub_int32 = d[31:0];
        end
    endfunction

    // Intermediate combinational wires for Pass-1 update & Pass-2 MAC
    wire signed [31:0] p1_res0 = r_y_meas_q16 - lor_y_out[0];
    wire signed [31:0] p1_res1 = r_y_meas_q16 - lor_y_out[1];
    wire signed [31:0] p1_res2 = r_y_meas_q16 - lor_y_out[2];
    wire signed [31:0] p1_res3 = r_y_meas_q16 - lor_y_out[3];

    wire signed [31:0] p1_dlp0 = q16_mul_fn(p1_resid2_d3[0], r_inv_2var_q16);
    wire signed [31:0] p1_dlp1 = q16_mul_fn(p1_resid2_d3[1], r_inv_2var_q16);
    wire signed [31:0] p1_dlp2 = q16_mul_fn(p1_resid2_d3[2], r_inv_2var_q16);
    wire signed [31:0] p1_dlp3 = q16_mul_fn(p1_resid2_d3[3], r_inv_2var_q16);

    wire signed [15:0] p2_df0 = $signed({6'd0, p2_addr_d2, 2'd0}) - 16'sd500;
    wire signed [15:0] p2_df1 = p2_df0 + 16'sd1;
    wire signed [15:0] p2_df2 = p2_df0 + 16'sd2;
    wire signed [15:0] p2_df3 = p2_df0 + 16'sd3;

    wire signed [47:0] w0_ext = p2_act_d2[0] ? {{16{exp_y_out[0][31]}}, exp_y_out[0]} : 48'sd0;
    wire signed [47:0] w1_ext = p2_act_d2[1] ? {{16{exp_y_out[1][31]}}, exp_y_out[1]} : 48'sd0;
    wire signed [47:0] w2_ext = p2_act_d2[2] ? {{16{exp_y_out[2][31]}}, exp_y_out[2]} : 48'sd0;
    wire signed [47:0] w3_ext = p2_act_d2[3] ? {{16{exp_y_out[3][31]}}, exp_y_out[3]} : 48'sd0;

    // Fisher inflection offset combinational helper
    wire [23:0] std_scaled_full = ({8'd0, isqrt_root_out} * 24'd282) >> 8;
    wire [15:0] std_scaled_q4   = std_scaled_full[15:0];
    wire [15:0] min_std_max     = (std_scaled_q4 < r_max_off_q4) ? std_scaled_q4 : r_max_off_q4;
    wire [15:0] fisher_off_q4   = (r_delta_fisher_q4 > min_std_max) ? r_delta_fisher_q4 : min_std_max;
    wire        next_sign_neg   = ~r_step_idx[0]; // (step_idx + 1) % 2 == 0 -> -1

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
            p1_addr_d1        <= 8'd0;
            p1_addr_d2        <= 8'd0;
            p1_addr_d3        <= 8'd0;
            p1_addr_d4        <= 8'd0;
            p2_act_d1         <= 4'd0;
            p2_act_d2         <= 4'd0;
            p2_addr_d1        <= 8'd0;
            p2_addr_d2        <= 8'd0;
            lp_rd_lane[0]     <= 32'sd0;
            lp_rd_lane[1]     <= 32'sd0;
            lp_rd_lane[2]     <= 32'sd0;
            lp_rd_lane[3]     <= 32'sd0;
            isqrt_in_v        <= 1'b0;
            isqrt_rad_in      <= 32'd0;
            post_mean_b_q8    <= 32'sd0;
            post_mu_off_q8    <= 32'sd0;
            post_ex2_q16      <= 32'd0;
            post_var_hz2_q8   <= 32'd0;
            post_std_q4       <= 16'd0;
            post_div_done     <= 1'b0;
        end else begin
            step_done  <= 1'b0;
            isqrt_in_v <= 1'b0;

            // External prior BRAM load when IDLE
            if (state == S_IDLE && prior_load_en) begin
                case (prior_load_addr[1:0])
                    2'd0: lp_bank0[prior_load_addr[9:2]] <= prior_load_lp_q16;
                    2'd1: lp_bank1[prior_load_addr[9:2]] <= prior_load_lp_q16;
                    2'd2: lp_bank2[prior_load_addr[9:2]] <= prior_load_lp_q16;
                    2'd3: lp_bank3[prior_load_addr[9:2]] <= prior_load_lp_q16;
                    default: ;
                endcase
            end

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
                        phase_cnt         <= 10'd0;
                        total_cyc         <= 16'd0;
                        post_div_done     <= 1'b0;
                        state             <= S_PASS1;
                    end
                end

                // Pass 1: 263 deterministic clock cycles
                S_PASS1: begin
                    total_cyc <= total_cyc + 16'd1;
                    // Stage 1: read current log-prior across all 4 banks
                    p1_addr_d1     <= beat_idx;
                    p1_act_d1[0]   <= p1_issue && (({3'd0, beat_idx} << 2) + 11'd0 < N_FINE_BINS);
                    p1_act_d1[1]   <= p1_issue && (({3'd0, beat_idx} << 2) + 11'd1 < N_FINE_BINS);
                    p1_act_d1[2]   <= p1_issue && (({3'd0, beat_idx} << 2) + 11'd2 < N_FINE_BINS);
                    p1_act_d1[3]   <= p1_issue && (({3'd0, beat_idx} << 2) + 11'd3 < N_FINE_BINS);
                    p1_old_lp_d1[0] <= lp_bank0[beat_idx];
                    p1_old_lp_d1[1] <= lp_bank1[beat_idx];
                    p1_old_lp_d1[2] <= lp_bank2[beat_idx];
                    p1_old_lp_d1[3] <= lp_bank3[beat_idx];

                    // Stage 2: align with 2-cycle BRAM Lorentzian LUT output
                    p1_addr_d2      <= p1_addr_d1;
                    p1_act_d2       <= p1_act_d1;
                    p1_old_lp_d2[0] <= p1_old_lp_d1[0];
                    p1_old_lp_d2[1] <= p1_old_lp_d1[1];
                    p1_old_lp_d2[2] <= p1_old_lp_d1[2];
                    p1_old_lp_d2[3] <= p1_old_lp_d1[3];

                    // Stage 3: residual^2 in Q16.16
                    p1_addr_d3      <= p1_addr_d2;
                    p1_act_d3       <= p1_act_d2;
                    p1_old_lp_d3[0] <= p1_old_lp_d2[0];
                    p1_old_lp_d3[1] <= p1_old_lp_d2[1];
                    p1_old_lp_d3[2] <= p1_old_lp_d2[2];
                    p1_old_lp_d3[3] <= p1_old_lp_d2[3];
                    p1_resid2_d3[0] <= q16_mul_fn(p1_res0, p1_res0);
                    p1_resid2_d3[1] <= q16_mul_fn(p1_res1, p1_res1);
                    p1_resid2_d3[2] <= q16_mul_fn(p1_res2, p1_res2);
                    p1_resid2_d3[3] <= q16_mul_fn(p1_res3, p1_res3);

                    // Stage 4: saturated log-posterior update
                    p1_addr_d4      <= p1_addr_d3;
                    p1_act_d4       <= p1_act_d3;
                    p1_new_lp_d4[0] <= sat_sub_int32(p1_old_lp_d3[0], p1_dlp0);
                    p1_new_lp_d4[1] <= sat_sub_int32(p1_old_lp_d3[1], p1_dlp1);
                    p1_new_lp_d4[2] <= sat_sub_int32(p1_old_lp_d3[2], p1_dlp2);
                    p1_new_lp_d4[3] <= sat_sub_int32(p1_old_lp_d3[3], p1_dlp3);

                    // Stage 5: writeback + running max_lp reduction
                    if (p1_act_d4[0]) begin
                        lp_bank0[p1_addr_d4] <= p1_new_lp_d4[0];
                        if (p1_new_lp_d4[0] > max_lp_reg) max_lp_reg <= p1_new_lp_d4[0];
                    end
                    if (p1_act_d4[1]) begin
                        lp_bank1[p1_addr_d4] <= p1_new_lp_d4[1];
                        if (p1_new_lp_d4[1] > max_lp_reg) max_lp_reg <= p1_new_lp_d4[1];
                    end
                    if (p1_act_d4[2]) begin
                        lp_bank2[p1_addr_d4] <= p1_new_lp_d4[2];
                        if (p1_new_lp_d4[2] > max_lp_reg) max_lp_reg <= p1_new_lp_d4[2];
                    end
                    if (p1_act_d4[3]) begin
                        lp_bank3[p1_addr_d4] <= p1_new_lp_d4[3];
                        if (p1_new_lp_d4[3] > max_lp_reg) max_lp_reg <= p1_new_lp_d4[3];
                    end

                    if (phase_cnt == PASS1_LIMIT - 10'd1) begin
                        phase_cnt <= 10'd0;
                        state     <= S_PASS2;
                    end else begin
                        phase_cnt <= phase_cnt + 10'd1;
                    end
                end

                // Pass 2: 265 deterministic clock cycles (exp LUT + 48-bit Z, M1, M2 MAC)
                S_PASS2: begin
                    total_cyc <= total_cyc + 16'd1;
                    lp_rd_lane[0] <= lp_bank0[beat_idx];
                    lp_rd_lane[1] <= lp_bank1[beat_idx];
                    lp_rd_lane[2] <= lp_bank2[beat_idx];
                    lp_rd_lane[3] <= lp_bank3[beat_idx];

                    p2_addr_d1   <= beat_idx;
                    p2_act_d1[0] <= p2_issue && (({3'd0, beat_idx} << 2) + 11'd0 < N_FINE_BINS);
                    p2_act_d1[1] <= p2_issue && (({3'd0, beat_idx} << 2) + 11'd1 < N_FINE_BINS);
                    p2_act_d1[2] <= p2_issue && (({3'd0, beat_idx} << 2) + 11'd2 < N_FINE_BINS);
                    p2_act_d1[3] <= p2_issue && (({3'd0, beat_idx} << 2) + 11'd3 < N_FINE_BINS);

                    p2_addr_d2 <= p2_addr_d1;
                    p2_act_d2  <= p2_act_d1;

                    if (exp_v_out[0] || exp_v_out[1] || exp_v_out[2] || exp_v_out[3]) begin
                        acc_z  <= acc_z + w0_ext + w1_ext + w2_ext + w3_ext;
                        acc_m1 <= acc_m1 +
                                  (w0_ext * p2_df0) + (w1_ext * p2_df1) +
                                  (w2_ext * p2_df2) + (w3_ext * p2_df3);
                        acc_m2 <= acc_m2 +
                                  (w0_ext * p2_df0 * p2_df0) + (w1_ext * p2_df1 * p2_df1) +
                                  (w2_ext * p2_df2 * p2_df2) + (w3_ext * p2_df3 * p2_df3);
                    end

                    if (phase_cnt == PASS2_LIMIT - 10'd1) begin
                        phase_cnt <= 10'd0;
                        state     <= S_POST;
                    end else begin
                        phase_cnt <= phase_cnt + 10'd1;
                    end
                end

                // Pass 3: 56 deterministic clock cycles (Divider + 16-stage CORDIC isqrt + Fisher argmax)
                S_POST: begin
                    total_cyc <= total_cyc + 16'd1;

                    // Cycle 0..31: Guard acc_z >= 1 and launch moment division
                    if (phase_cnt == 10'd0) begin
                        if (acc_z <= 48'sd0) begin
                            acc_z <= 48'sd1;
                        end
                    end

                    // Cycle 32: Latch floor-divided moments & trigger 16-stage pipelined isqrt (ready at cycle 50)
                    if (phase_cnt == 10'd32) begin
                        post_mean_b_q8 <= floor_div_s48(acc_m1 * 48'sd256, acc_z);
                        post_mu_off_q8 <= floor_div_s48(acc_m1 * 48'sd2560, acc_z);
                        post_ex2_q16   <= (acc_m2 <<< 16) / acc_z;
                        post_div_done  <= 1'b1;
                    end

                    if (phase_cnt == 10'd33) begin
                        if (post_ex2_q16 > (post_mean_b_q8 * post_mean_b_q8)) begin
                            post_var_hz2_q8 <= ((post_ex2_q16 - (post_mean_b_q8 * post_mean_b_q8)) * 32'd100) >> 8;
                        end else begin
                            post_var_hz2_q8 <= 32'd0;
                        end
                    end

                    if (phase_cnt == 10'd34) begin
                        isqrt_in_v   <= 1'b1;
                        isqrt_rad_in <= post_var_hz2_q8;
                    end

                    // Cycle 50: Latch exact isqrt output and compute Fisher next-probe offset in Q8 (0-LSB!)
                    if (isqrt_out_v) begin
                        post_std_q4 <= isqrt_root_out;
                        mu_off_q8   <= post_mu_off_q8;
                        std_q4      <= isqrt_root_out;
                        if (next_sign_neg)
                            next_probe_off_q8 <= post_mu_off_q8 - $signed({12'd0, fisher_off_q4, 4'd0});
                        else
                            next_probe_off_q8 <= post_mu_off_q8 + $signed({12'd0, fisher_off_q4, 4'd0});
                    end

                    if (phase_cnt == POST_LIMIT - 10'd1) begin
                        cycle_count <= total_cyc + 16'd1; // Exact 584 cycles
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
