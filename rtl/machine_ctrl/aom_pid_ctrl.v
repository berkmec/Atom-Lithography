// aom_pid_ctrl.v - Bit-Exact Q16.16 Anti-Windup Discrete AOM Laser Power & Pyrometer PID
// BOM Traceability: S5.3-03, S5.5-01, S5.5-03, S1.4-03
// Reference Model : src/machine_control/auto_recal.py (Mode A closed-loop AOM PID)
// Target Clock    : 100.0 MHz (10.0 ns period), 100 kHz photodiode/pyrometer sample ticks
//
// Features:
//   - Bit-exact signed Q16.16 fixed-point arithmetic (1.0 = 32'sd65536 = 32'h0001_0000)
//   - 6-state pipelined FSM (5 cycles = 50 ns @ 100 MHz, 200x margin vs 10 us sample period):
//       ST_IDLE -> ST_ERR_PYRO -> ST_MUL_PD -> ST_SUM_CLAMP -> ST_MUL_AW -> ST_UPDATE
//     Isolates every 32x32 multiply from saturating add/clamp trees for clean timing closure!
//   - Built-in 2-FF async-assert / sync-deassert reset synchronizer (`rst_sync_n`).
//   - Hard-wired non-bypassable over-temperature abort (temp_meas_k >= 1687 K Si T_melt)
//     and hard-wired `interlock_abort` override -> immediate ZERO AOM drive!
//   - ZERO combinational '/' operators, ZERO latches, ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module aom_pid_ctrl #(
    parameter signed [31:0] DEFAULT_KP_Q16       = 32'sd27525, // 0.42 * 65536
    parameter signed [31:0] DEFAULT_KI_Q16       = 32'sd23593, // 0.36 * 65536
    parameter signed [31:0] DEFAULT_KD_Q16       = 32'sd3277,  // 0.05 * 65536
    parameter signed [31:0] DEFAULT_KAW_Q16      = 32'sd42598, // 0.65 * 65536
    parameter signed [31:0] DEFAULT_MIN_GAIN_Q16 = 32'sd42598, // 0.65 * 65536
    parameter signed [31:0] DEFAULT_MAX_GAIN_Q16 = 32'sd91750, // 1.40 * 65536
    parameter signed [31:0] DEFAULT_SETPOINT_Q16 = 32'sd65536, // 1.00 * 65536
    parameter signed [31:0] DEFAULT_BIAS_Q16     = 32'sd65536, // 1.00 * 65536
    parameter signed [31:0] DEFAULT_KT_PYRO_Q16  = 32'sd39     // ~0.60 / 1000 K in Q16.16
) (
    input  wire               clk,
    input  wire               rst_n,

    // Hard-wired safety interlock abort (active-HIGH -> zero AOM drive)
    input  wire               interlock_abort,

    // Control inputs
    input  wire               enable,
    input  wire               pyro_en,
    input  wire               abort_clr,
    input  wire               state_reset,
    input  wire        [3:0]  dead_time_taps, // 0..15 taps

    // Sample inputs (100 kHz photodiode Q16.16 + 10 us pyrometer Kelvin)
    input  wire               sample_valid,
    input  wire signed [31:0] meas_q16,
    input  wire        [15:0] temp_meas_k,    // Unsigned Kelvin (hardwired abort >= 1687 K)
    input  wire        [15:0] temp_ref_k,     // Unsigned reference Kelvin

    // Programmable Q16.16 gains & limits
    input  wire               cfg_use_ext,
    input  wire signed [31:0] cfg_kp_q16,
    input  wire signed [31:0] cfg_ki_q16,
    input  wire signed [31:0] cfg_kd_q16,
    input  wire signed [31:0] cfg_kaw_q16,
    input  wire signed [31:0] cfg_min_gain_q16,
    input  wire signed [31:0] cfg_max_gain_q16,
    input  wire signed [31:0] cfg_setpoint_q16,
    input  wire signed [31:0] cfg_bias_q16,
    input  wire signed [31:0] cfg_kt_pyro_q16,

    // Outputs
    output wire               busy,
    output reg                out_valid,
    output wire               aom_rf_en,
    output wire signed [31:0] aom_drive_q16,
    output reg  signed [31:0] u_raw_q16,
    output reg  signed [31:0] integ_q16,
    output reg                saturated,
    output reg                overtemp_latched,
    output wire               abort_active,
    output reg         [15:0] last_temp_k
);
    localparam [15:0] T_MELT_SI_K        = 16'd1687;
    localparam [15:0] T_PYRO_MIN_K       = 16'd480;
    localparam signed [31:0] INT32_MAX_V =  32'sd2147483647;
    localparam signed [31:0] INT32_MIN_V = -32'sd2147483647 - 32'sd1;

    // 6-state deterministic pipeline (5 cycles sample_valid -> out_valid)
    localparam [2:0] ST_IDLE      = 3'd0;
    localparam [2:0] ST_ERR_PYRO  = 3'd1;
    localparam [2:0] ST_MUL_PD    = 3'd2;
    localparam [2:0] ST_SUM_CLAMP = 3'd3;
    localparam [2:0] ST_MUL_AW    = 3'd4;
    localparam [2:0] ST_UPDATE    = 3'd5;

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

    // Effective gains
    wire signed [31:0] kp_eff       = cfg_use_ext ? cfg_kp_q16       : DEFAULT_KP_Q16;
    wire signed [31:0] ki_eff       = cfg_use_ext ? cfg_ki_q16       : DEFAULT_KI_Q16;
    wire signed [31:0] kd_eff       = cfg_use_ext ? cfg_kd_q16       : DEFAULT_KD_Q16;
    wire signed [31:0] kaw_eff      = cfg_use_ext ? cfg_kaw_q16      : DEFAULT_KAW_Q16;
    wire signed [31:0] min_gain_eff = cfg_use_ext ? cfg_min_gain_q16 : DEFAULT_MIN_GAIN_Q16;
    wire signed [31:0] max_gain_eff = cfg_use_ext ? cfg_max_gain_q16 : DEFAULT_MAX_GAIN_Q16;
    wire signed [31:0] setpoint_eff = cfg_use_ext ? cfg_setpoint_q16 : DEFAULT_SETPOINT_Q16;
    wire signed [31:0] bias_eff     = cfg_use_ext ? cfg_bias_q16     : DEFAULT_BIAS_Q16;
    wire signed [31:0] kt_pyro_eff  = cfg_use_ext ? cfg_kt_pyro_q16  : DEFAULT_KT_PYRO_Q16;

    // Hardwired over-temperature detector (non-bypassable)
    wire overtemp_hit = (temp_meas_k >= T_MELT_SI_K);
    assign abort_active = interlock_abort | overtemp_hit | overtemp_latched;
    assign aom_rf_en    = enable & (~abort_active);

    // Pipeline & state registers
    reg [2:0]         state;
    reg signed [31:0] r_aom_drive_q16;
    reg signed [31:0] prev_meas_q16;
    reg signed [31:0] d_filt_q16;
    reg signed [31:0] err_p_r;
    reg signed [31:0] dt_k_r;
    reg               pyro_active_r;
    reg signed [31:0] err_r;
    reg signed [63:0] p_prod_r;
    reg signed [63:0] i_prod_r;
    reg signed [63:0] d_prod_r;
    reg signed [31:0] aw_err_r;
    reg signed [63:0] aw_prod_r;
    reg signed [31:0] i_term_r;
    reg signed [31:0] g_cmd_r;

    // 16-tap dead-time delay shift register
    reg signed [31:0] delay_sr [0:15];

    assign busy          = (state != ST_IDLE);
    assign aom_drive_q16 = abort_active ? 32'sd0 : r_aom_drive_q16;

    function signed [31:0] sat_add32;
        input signed [31:0] a;
        input signed [31:0] b;
        reg signed [32:0] s;
        begin
            s = {a[31], a} + {b[31], b};
            if (s[32] != s[31]) begin
                sat_add32 = s[32] ? INT32_MIN_V : INT32_MAX_V;
            end else begin
                sat_add32 = s[31:0];
            end
        end
    endfunction

    function signed [31:0] sat_sub32;
        input signed [31:0] a;
        input signed [31:0] b;
        reg signed [32:0] d;
        begin
            d = {a[31], a} - {b[31], b};
            if (d[32] != d[31]) begin
                sat_sub32 = d[32] ? INT32_MIN_V : INT32_MAX_V;
            end else begin
                sat_sub32 = d[31:0];
            end
        end
    endfunction

    // Stage 0 combinational (pure add/sub, ZERO multiply)
    wire signed [31:0] err_p_c     = sat_sub32(setpoint_eff, meas_q16);
    wire signed [31:0] dt_k_c      = $signed({16'd0, temp_ref_k}) - $signed({16'd0, temp_meas_k});
    wire               pyro_act_c  = pyro_en && (temp_ref_k > T_PYRO_MIN_K);
    wire signed [31:0] d_raw_c     = sat_sub32(prev_meas_q16, meas_q16);
    wire signed [32:0] d_sum33_c   = {d_filt_q16[31], d_filt_q16} + {d_raw_c[31], d_raw_c};
    wire signed [31:0] d_filt_next = $signed(d_sum33_c[32:1]);

    // Stage 1 combinational (isolated pyrometer multiply from registered dt_k_r)
    wire signed [63:0] err_t_p64   = {{32{dt_k_r[31]}}, dt_k_r} * {{32{kt_pyro_eff[31]}}, kt_pyro_eff};
    wire               err_t_ovf   = (err_t_p64[63:31] != 33'd0) && (err_t_p64[63:31] != {33{1'b1}});
    wire signed [31:0] err_t_sat   = err_t_ovf ? (err_t_p64[63] ? INT32_MIN_V : INT32_MAX_V) : err_t_p64[31:0];
    wire signed [31:0] err_t_c     = pyro_active_r ? err_t_sat : 32'sd0;
    wire signed [31:0] err_tot_c   = sat_add32(err_p_r, err_t_c);

    // Stage 3 combinational Q16.16 round + sum + clamp (NO multiply in this stage!)
    wire signed [63:0] p_rnd64 = p_prod_r + 64'sd32768;
    wire signed [63:0] i_rnd64 = i_prod_r + 64'sd32768;
    wire signed [63:0] d_rnd64 = d_prod_r + 64'sd32768;
    wire signed [63:0] a_rnd64 = aw_prod_r + 64'sd32768;

    wire p_ovf = (p_rnd64[63:47] != 17'h00000) && (p_rnd64[63:47] != 17'h1FFFF);
    wire i_ovf = (i_rnd64[63:47] != 17'h00000) && (i_rnd64[63:47] != 17'h1FFFF);
    wire d_ovf = (d_rnd64[63:47] != 17'h00000) && (d_rnd64[63:47] != 17'h1FFFF);
    wire a_ovf = (a_rnd64[63:47] != 17'h00000) && (a_rnd64[63:47] != 17'h1FFFF);

    wire signed [31:0] p_term_c  = p_ovf ? (p_rnd64[63] ? INT32_MIN_V : INT32_MAX_V) : $signed(p_rnd64[47:16]);
    wire signed [31:0] i_term_c  = i_ovf ? (i_rnd64[63] ? INT32_MIN_V : INT32_MAX_V) : $signed(i_rnd64[47:16]);
    wire signed [31:0] d_term_c  = d_ovf ? (d_rnd64[63] ? INT32_MIN_V : INT32_MAX_V) : $signed(d_rnd64[47:16]);
    wire signed [31:0] aw_term_c = a_ovf ? (a_rnd64[63] ? INT32_MIN_V : INT32_MAX_V) : $signed(a_rnd64[47:16]);

    wire signed [31:0] sum_bp_c  = sat_add32(bias_eff, p_term_c);
    wire signed [31:0] sum_id_c  = sat_add32(integ_q16, d_term_c);
    wire signed [31:0] u_raw_c   = sat_add32(sum_bp_c, sum_id_c);
    wire signed [31:0] g_cmd_c   = (u_raw_c < min_gain_eff) ? min_gain_eff :
                                   ((u_raw_c > max_gain_eff) ? max_gain_eff : u_raw_c);
    wire signed [31:0] aw_err_c  = sat_sub32(g_cmd_c, u_raw_c);

    // Stage 5 combinational integrator update & delay-line tap select
    wire signed [31:0] di_tot_c    = sat_add32(i_term_r, aw_term_c);
    wire signed [31:0] integ_nxt_c = sat_add32(integ_q16, di_tot_c);
    wire        [3:0]  tap_idx_c   = (dead_time_taps == 4'd0) ? 4'd0 : (dead_time_taps - 4'd1);
    wire signed [31:0] drive_nxt_c = (dead_time_taps == 4'd0) ? g_cmd_r : delay_sr[tap_idx_c];

    wire _unused_ok = &{1'b0, d_sum33_c[0], p_rnd64[15:0], i_rnd64[15:0], d_rnd64[15:0], a_rnd64[15:0]};

    integer k;

    always @(posedge clk) begin
        if (!rst_sync_n) begin
            state            <= ST_IDLE;
            out_valid        <= 1'b0;
            r_aom_drive_q16  <= 32'sd0;
            u_raw_q16        <= DEFAULT_BIAS_Q16;
            integ_q16        <= 32'sd0;
            prev_meas_q16    <= DEFAULT_SETPOINT_Q16;
            d_filt_q16       <= 32'sd0;
            err_p_r          <= 32'sd0;
            dt_k_r           <= 32'sd0;
            pyro_active_r    <= 1'b0;
            err_r            <= 32'sd0;
            p_prod_r         <= 64'sd0;
            i_prod_r         <= 64'sd0;
            d_prod_r         <= 64'sd0;
            aw_err_r         <= 32'sd0;
            aw_prod_r        <= 64'sd0;
            i_term_r         <= 32'sd0;
            g_cmd_r          <= DEFAULT_BIAS_Q16;
            saturated        <= 1'b0;
            overtemp_latched <= 1'b0;
            last_temp_k      <= 16'd300;
            for (k = 0; k < 16; k = k + 1) begin
                delay_sr[k] <= DEFAULT_BIAS_Q16;
            end
        end else begin
            out_valid   <= 1'b0;
            last_temp_k <= temp_meas_k;

            if (interlock_abort || overtemp_hit) begin
                if (overtemp_hit) begin
                    overtemp_latched <= 1'b1;
                end
                r_aom_drive_q16 <= 32'sd0;
                u_raw_q16       <= 32'sd0;
                integ_q16       <= 32'sd0;
                d_filt_q16      <= 32'sd0;
                saturated       <= 1'b0;
                state           <= ST_IDLE;
                for (k = 0; k < 16; k = k + 1) begin
                    delay_sr[k] <= 32'sd0;
                end
            end else if (overtemp_latched) begin
                r_aom_drive_q16 <= 32'sd0;
                state           <= ST_IDLE;
                if (abort_clr) begin
                    overtemp_latched <= 1'b0;
                    prev_meas_q16    <= setpoint_eff;
                    for (k = 0; k < 16; k = k + 1) begin
                        delay_sr[k] <= bias_eff;
                    end
                end
            end else if (state_reset) begin
                state           <= ST_IDLE;
                integ_q16       <= 32'sd0;
                d_filt_q16      <= 32'sd0;
                prev_meas_q16   <= setpoint_eff;
                u_raw_q16       <= bias_eff;
                r_aom_drive_q16 <= enable ? bias_eff : 32'sd0;
                saturated       <= 1'b0;
                for (k = 0; k < 16; k = k + 1) begin
                    delay_sr[k] <= bias_eff;
                end
            end else if (!enable) begin
                state           <= ST_IDLE;
                r_aom_drive_q16 <= 32'sd0;
            end else begin
                case (state)
                    ST_IDLE: begin
                        if (sample_valid) begin
                            err_p_r       <= err_p_c;
                            dt_k_r        <= dt_k_c;
                            pyro_active_r <= pyro_act_c;
                            d_filt_q16    <= d_filt_next;
                            prev_meas_q16 <= meas_q16;
                            state         <= ST_ERR_PYRO;
                        end
                    end

                    ST_ERR_PYRO: begin
                        err_r <= err_tot_c;
                        state <= ST_MUL_PD;
                    end

                    ST_MUL_PD: begin
                        p_prod_r <= {{32{kp_eff[31]}}, kp_eff} * {{32{err_r[31]}}, err_r};
                        i_prod_r <= {{32{ki_eff[31]}}, ki_eff} * {{32{err_r[31]}}, err_r};
                        d_prod_r <= {{32{kd_eff[31]}}, kd_eff} * {{32{d_filt_q16[31]}}, d_filt_q16};
                        state    <= ST_SUM_CLAMP;
                    end

                    ST_SUM_CLAMP: begin
                        u_raw_q16 <= u_raw_c;
                        g_cmd_r   <= g_cmd_c;
                        i_term_r  <= i_term_c;
                        saturated <= (g_cmd_c != u_raw_c);
                        aw_err_r  <= aw_err_c;
                        state     <= ST_MUL_AW;
                    end

                    ST_MUL_AW: begin
                        aw_prod_r <= {{32{kaw_eff[31]}}, kaw_eff} * {{32{aw_err_r[31]}}, aw_err_r};
                        state     <= ST_UPDATE;
                    end

                    ST_UPDATE: begin
                        integ_q16       <= integ_nxt_c;
                        r_aom_drive_q16 <= drive_nxt_c;
                        delay_sr[0]     <= g_cmd_r;
                        for (k = 1; k < 16; k = k + 1) begin
                            delay_sr[k] <= delay_sr[k - 1];
                        end
                        out_valid <= 1'b1;
                        state     <= ST_IDLE;
                    end

                    default: begin
                        state <= ST_IDLE;
                    end
                endcase
            end
        end
    end
endmodule
