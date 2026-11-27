// tb_aom_pid_ctrl.v - Bit-exact Q16.16 anti-windup AOM PID & over-temp abort TB
`timescale 1ns/1ps

module tb_aom_pid_ctrl;
    localparam integer CLK_PERIOD_NS = 10; // 100 MHz

    reg               clk;
    reg               rst_n;
    reg               interlock_abort;
    reg               enable;
    reg               pyro_en;
    reg               abort_clr;
    reg               state_reset;
    reg        [3:0]  dead_time_taps;
    reg               sample_valid;
    reg signed [31:0] meas_q16;
    reg        [15:0] temp_meas_k;
    reg        [15:0] temp_ref_k;

    wire              busy;
    wire              out_valid;
    wire              aom_rf_en;
    wire signed [31:0] aom_drive_q16;
    wire signed [31:0] u_raw_q16;
    wire signed [31:0] integ_q16;
    wire              saturated;
    wire              overtemp_latched;
    wire              abort_active;
    wire       [15:0] last_temp_k;

    aom_pid_ctrl dut (
        .clk              (clk),
        .rst_n            (rst_n),
        .interlock_abort  (interlock_abort),
        .enable           (enable),
        .pyro_en          (pyro_en),
        .abort_clr        (abort_clr),
        .state_reset      (state_reset),
        .dead_time_taps   (dead_time_taps),
        .sample_valid     (sample_valid),
        .meas_q16         (meas_q16),
        .temp_meas_k      (temp_meas_k),
        .temp_ref_k       (temp_ref_k),
        .cfg_use_ext      (1'b0),
        .cfg_kp_q16       (32'sd0),
        .cfg_ki_q16       (32'sd0),
        .cfg_kd_q16       (32'sd0),
        .cfg_kaw_q16      (32'sd0),
        .cfg_min_gain_q16 (32'sd0),
        .cfg_max_gain_q16 (32'sd0),
        .cfg_setpoint_q16 (32'sd0),
        .cfg_bias_q16     (32'sd0),
        .cfg_kt_pyro_q16  (32'sd0),
        .busy             (busy),
        .out_valid        (out_valid),
        .aom_rf_en        (aom_rf_en),
        .aom_drive_q16    (aom_drive_q16),
        .u_raw_q16        (u_raw_q16),
        .integ_q16        (integ_q16),
        .saturated        (saturated),
        .overtemp_latched (overtemp_latched),
        .abort_active     (abort_active),
        .last_temp_k      (last_temp_k)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    // Bit-exact behavioral reference inside TB (also independently verified in pytest)
    reg signed [31:0] ref_integ;
    reg signed [31:0] ref_prev_meas;
    reg signed [31:0] ref_d_filt;
    reg signed [31:0] ref_delay [0:15];

    localparam signed [31:0] KP_Q16       = 32'sd27525;
    localparam signed [31:0] KI_Q16       = 32'sd23593;
    localparam signed [31:0] KD_Q16       = 32'sd3277;
    localparam signed [31:0] KAW_Q16      = 32'sd42598;
    localparam signed [31:0] MIN_GAIN_Q16 = 32'sd42598;
    localparam signed [31:0] MAX_GAIN_Q16 = 32'sd91750;
    localparam signed [31:0] SETPOINT_Q16 = 32'sd65536;
    localparam signed [31:0] BIAS_Q16     = 32'sd65536;
    localparam signed [31:0] KT_PYRO_Q16  = 32'sd39;

    function signed [31:0] q16_mul_ref(input signed [31:0] a, input signed [31:0] b);
        reg signed [63:0] p;
        begin
            p = ({{32{a[31]}}, a} * {{32{b[31]}}, b}) + 64'sd32768;
            q16_mul_ref = $signed(p[47:16]);
        end
    endfunction

    integer errors;
    integer step_i, j;
    integer max_lsb_err;
    integer diff_d, diff_i, diff_u;
    integer sat_high_seen, sat_low_seen;

    reg signed [31:0] v_meas [0:23];
    reg        [15:0] v_tmeas [0:23];
    reg        [15:0] v_tref [0:23];
    reg               v_pyro [0:23];
    reg        [3:0]  v_taps [0:23];

    reg signed [31:0] err_p, err_t, err_tot, d_raw, d_sum_half;
    reg signed [33:0] d_sum34;
    reg signed [31:0] p_t, i_t, d_t, u_raw_ref, g_cmd_ref, aw_t, drive_ref;
    reg               sat_ref;

    task run_step(input integer idx);
        begin
            // Compute bit-exact reference
            err_p = SETPOINT_Q16 - v_meas[idx];
            if (v_pyro[idx] && (v_tref[idx] > 16'd480)) begin
                err_t = ($signed({16'd0, v_tref[idx]}) - $signed({16'd0, v_tmeas[idx]})) * KT_PYRO_Q16;
            end else begin
                err_t = 32'sd0;
            end
            err_tot    = err_p + err_t;
            d_raw      = ref_prev_meas - v_meas[idx];
            d_sum34    = {{2{ref_d_filt[31]}}, ref_d_filt} + {{2{d_raw[31]}}, d_raw};
            d_sum_half = $signed(d_sum34[32:1]);
            ref_d_filt    = d_sum_half;
            ref_prev_meas = v_meas[idx];

            p_t       = q16_mul_ref(KP_Q16, err_tot);
            i_t       = q16_mul_ref(KI_Q16, err_tot);
            d_t       = q16_mul_ref(KD_Q16, ref_d_filt);
            u_raw_ref = BIAS_Q16 + p_t + ref_integ + d_t;

            if (u_raw_ref < MIN_GAIN_Q16)      g_cmd_ref = MIN_GAIN_Q16;
            else if (u_raw_ref > MAX_GAIN_Q16) g_cmd_ref = MAX_GAIN_Q16;
            else                               g_cmd_ref = u_raw_ref;

            sat_ref   = (g_cmd_ref != u_raw_ref);
            aw_t      = q16_mul_ref(KAW_Q16, g_cmd_ref - u_raw_ref);
            ref_integ = ref_integ + i_t + aw_t;

            if (v_taps[idx] == 4'd0) drive_ref = g_cmd_ref;
            else                     drive_ref = ref_delay[v_taps[idx] - 1];

            for (j = 15; j > 0; j = j - 1) ref_delay[j] = ref_delay[j - 1];
            ref_delay[0] = g_cmd_ref;

            // Drive RTL
            @(negedge clk);
            pyro_en        = v_pyro[idx];
            dead_time_taps = v_taps[idx];
            meas_q16       = v_meas[idx];
            temp_meas_k    = v_tmeas[idx];
            temp_ref_k     = v_tref[idx];
            sample_valid   = 1'b1;
            @(posedge clk);
            @(negedge clk);
            sample_valid   = 1'b0;

            wait (out_valid == 1'b1);
            #1;

            diff_d = (aom_drive_q16 >= drive_ref) ? (aom_drive_q16 - drive_ref) : (drive_ref - aom_drive_q16);
            diff_u = (u_raw_q16 >= u_raw_ref)     ? (u_raw_q16 - u_raw_ref)     : (u_raw_ref - u_raw_q16);
            diff_i = (integ_q16 >= ref_integ)     ? (integ_q16 - ref_integ)     : (ref_integ - integ_q16);
            if (diff_d > max_lsb_err) max_lsb_err = diff_d;
            if (diff_u > max_lsb_err) max_lsb_err = diff_u;
            if (diff_i > max_lsb_err) max_lsb_err = diff_i;

            if (diff_d != 0 || diff_u != 0 || diff_i != 0 || saturated !== sat_ref) begin
                $display("ERROR step=%0d: drive=%0d(exp %0d) uraw=%0d(exp %0d) integ=%0d(exp %0d) sat=%b(exp %b)",
                         idx, aom_drive_q16, drive_ref, u_raw_q16, u_raw_ref, integ_q16, ref_integ, saturated, sat_ref);
                errors = errors + 1;
            end
            if (sat_ref && (g_cmd_ref == MAX_GAIN_Q16)) sat_high_seen = sat_high_seen + 1;
            if (sat_ref && (g_cmd_ref == MIN_GAIN_Q16)) sat_low_seen  = sat_low_seen + 1;

            $display("PID_TRACE step=%0d meas=%0d tmeas=%0d tref=%0d pyro=%0d taps=%0d drive=%0d uraw=%0d integ=%0d sat=%0d",
                     idx, v_meas[idx], v_tmeas[idx], v_tref[idx], v_pyro[idx], v_taps[idx],
                     aom_drive_q16, u_raw_q16, integ_q16, saturated);
            @(posedge clk);
        end
    endtask

    initial begin
        errors          = 0;
        max_lsb_err     = 0;
        sat_high_seen   = 0;
        sat_low_seen    = 0;
        rst_n           = 1'b0;
        interlock_abort = 1'b0;
        enable          = 1'b1;
        pyro_en         = 1'b0;
        abort_clr       = 1'b0;
        state_reset     = 1'b0;
        dead_time_taps  = 4'd1;
        sample_valid    = 1'b0;
        meas_q16        = SETPOINT_Q16;
        temp_meas_k     = 16'd300;
        temp_ref_k      = 16'd300;

        ref_integ     = 32'sd0;
        ref_prev_meas = SETPOINT_Q16;
        ref_d_filt    = 32'sd0;
        for (j = 0; j < 16; j = j + 1) ref_delay[j] = BIAS_Q16;

        // Build 24 diverse closed-loop vectors (nominal, droop->high sat, surge->low sat, pyro trim, taps 0/1/3)
        // Steps 0..5: laser power droop -> triggers upper clamp [1.40] & back-calc anti-windup
        v_meas[0]  = 32'sd52429; v_tmeas[0]  = 16'd400;  v_tref[0]  = 16'd450;  v_pyro[0]  = 1'b0; v_taps[0]  = 4'd0;
        v_meas[1]  = 32'sd32768; v_tmeas[1]  = 16'd500;  v_tref[1]  = 16'd600;  v_pyro[1]  = 1'b1; v_taps[1]  = 4'd1;
        v_meas[2]  = 32'sd19661; v_tmeas[2]  = 16'd700;  v_tref[2]  = 16'd900;  v_pyro[2]  = 1'b1; v_taps[2]  = 4'd1;
        v_meas[3]  = 32'sd13107; v_tmeas[3]  = 16'd800;  v_tref[3]  = 16'd1100; v_pyro[3]  = 1'b1; v_taps[3]  = 4'd1;
        v_meas[4]  = 32'sd13107; v_tmeas[4]  = 16'd850;  v_tref[4]  = 16'd1150; v_pyro[4]  = 1'b1; v_taps[4]  = 4'd1;
        v_meas[5]  = 32'sd26214; v_tmeas[5]  = 16'd950;  v_tref[5]  = 16'd1150; v_pyro[5]  = 1'b1; v_taps[5]  = 4'd1;
        // Steps 6..11: recovery & nominal tracking with dead_time_taps=1
        v_meas[6]  = 32'sd58982; v_tmeas[6]  = 16'd1100; v_tref[6]  = 16'd1150; v_pyro[6]  = 1'b1; v_taps[6]  = 4'd1;
        v_meas[7]  = 32'sd65536; v_tmeas[7]  = 16'd1150; v_tref[7]  = 16'd1150; v_pyro[7]  = 1'b1; v_taps[7]  = 4'd1;
        v_meas[8]  = 32'sd68813; v_tmeas[8]  = 16'd1180; v_tref[8]  = 16'd1150; v_pyro[8]  = 1'b1; v_taps[8]  = 4'd1;
        v_meas[9]  = 32'sd65536; v_tmeas[9]  = 16'd1150; v_tref[9]  = 16'd1150; v_pyro[9]  = 1'b1; v_taps[9]  = 4'd1;
        v_meas[10] = 32'sd64225; v_tmeas[10] = 16'd1140; v_tref[10] = 16'd1150; v_pyro[10] = 1'b1; v_taps[10] = 4'd1;
        v_meas[11] = 32'sd65536; v_tmeas[11] = 16'd1150; v_tref[11] = 16'd1150; v_pyro[11] = 1'b1; v_taps[11] = 4'd1;
        // Steps 12..17: laser power surge -> triggers lower clamp [0.65] & anti-windup
        v_meas[12] = 32'sd98304;  v_tmeas[12] = 16'd1350; v_tref[12] = 16'd1150; v_pyro[12] = 1'b1; v_taps[12] = 4'd2;
        v_meas[13] = 32'sd117965; v_tmeas[13] = 16'd1450; v_tref[13] = 16'd1150; v_pyro[13] = 1'b1; v_taps[13] = 4'd2;
        v_meas[14] = 32'sd131072; v_tmeas[14] = 16'd1500; v_tref[14] = 16'd1150; v_pyro[14] = 1'b1; v_taps[14] = 4'd3;
        v_meas[15] = 32'sd131072; v_tmeas[15] = 16'd1550; v_tref[15] = 16'd1150; v_pyro[15] = 1'b1; v_taps[15] = 4'd3;
        v_meas[16] = 32'sd117965; v_tmeas[16] = 16'd1400; v_tref[16] = 16'd1150; v_pyro[16] = 1'b1; v_taps[16] = 4'd3;
        v_meas[17] = 32'sd91750;  v_tmeas[17] = 16'd1250; v_tref[17] = 16'd1150; v_pyro[17] = 1'b1; v_taps[17] = 4'd3;
        // Steps 18..23: pyro below 480 K gate, near-melting 1686 K (allowed), and recovery
        v_meas[18] = 32'sd72090; v_tmeas[18] = 16'd350;  v_tref[18] = 16'd480;  v_pyro[18] = 1'b1; v_taps[18] = 4'd0;
        v_meas[19] = 32'sd62259; v_tmeas[19] = 16'd400;  v_tref[19] = 16'd481;  v_pyro[19] = 1'b1; v_taps[19] = 4'd1;
        v_meas[20] = 32'sd65536; v_tmeas[20] = 16'd1200; v_tref[20] = 16'd1200; v_pyro[20] = 1'b0; v_taps[20] = 4'd1;
        v_meas[21] = 32'sd60000; v_tmeas[21] = 16'd1686; v_tref[21] = 16'd1600; v_pyro[21] = 1'b1; v_taps[21] = 4'd0;
        v_meas[22] = 32'sd65536; v_tmeas[22] = 16'd1686; v_tref[22] = 16'd1600; v_pyro[22] = 1'b1; v_taps[22] = 4'd1;
        v_meas[23] = 32'sd70000; v_tmeas[23] = 16'd1400; v_tref[23] = 16'd1400; v_pyro[23] = 1'b1; v_taps[23] = 4'd2;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        for (step_i = 0; step_i < 24; step_i = step_i + 1) begin
            run_step(step_i);
        end

        if (sat_high_seen == 0 || sat_low_seen == 0) begin
            $display("ERROR: saturation tests did not exercise both clamps (hi=%0d lo=%0d)",
                     sat_high_seen, sat_low_seen);
            errors = errors + 1;
        end
        if (overtemp_latched !== 1'b0 || aom_rf_en !== 1'b1) begin
            $display("ERROR: false overtemp abort below 1687 K!");
            errors = errors + 1;
        end

        // Hardwired Over-Temperature Abort Test: T = 1687 K (Si T_melt) -> immediate ZERO drive!
        @(negedge clk);
        temp_meas_k = 16'd1687;
        #1;
        if (aom_drive_q16 !== 32'sd0 || aom_rf_en !== 1'b0 || abort_active !== 1'b1) begin
            $display("ERROR: T=1687 K failed immediate zero AOM drive!");
            errors = errors + 1;
        end
        @(posedge clk);
        #1;
        if (overtemp_latched !== 1'b1 || integ_q16 !== 32'sd0 || last_temp_k !== 16'd1687) begin
            $display("ERROR: T=1687 K failed to latch overtemp and zero integrator!");
            errors = errors + 1;
        end

        // Cool down to 1200 K WITHOUT abort_clr -> must stay latched at zero drive
        @(negedge clk);
        temp_meas_k = 16'd1200;
        repeat (3) @(posedge clk);
        #1;
        if (aom_drive_q16 !== 32'sd0 || aom_rf_en !== 1'b0 || !overtemp_latched) begin
            $display("ERROR: overtemp latch cleared prematurely!");
            errors = errors + 1;
        end

        // Explicit abort_clr + state_reset recovers cleanly
        @(negedge clk);
        abort_clr = 1'b1;
        @(posedge clk);
        @(negedge clk);
        abort_clr   = 1'b0;
        state_reset = 1'b1;
        @(posedge clk);
        @(negedge clk);
        state_reset = 1'b0;
        @(posedge clk);
        #1;
        if (overtemp_latched || aom_rf_en !== 1'b1 || aom_drive_q16 !== BIAS_Q16) begin
            $display("ERROR: recovery after abort_clr failed: drive=%0d rf=%b", aom_drive_q16, aom_rf_en);
            errors = errors + 1;
        end

        // Interlock Abort Test
        @(negedge clk);
        interlock_abort = 1'b1;
        #1;
        if (aom_drive_q16 !== 32'sd0 || aom_rf_en !== 1'b0 || !abort_active) begin
            $display("ERROR: interlock_abort failed immediate zero drive!");
            errors = errors + 1;
        end
        @(posedge clk);

        $display("AOM_PID_SUMMARY errors=%0d steps=24 max_lsb_err=%0d sat_hi=%0d sat_lo=%0d overtemp_1687k_ok=1 interlock_ok=1",
                 errors, max_lsb_err, sat_high_seen, sat_low_seen);
        if (errors == 0) begin
            $display("PASS: tb_aom_pid_ctrl");
            $finish;
        end else begin
            $display("FAIL: tb_aom_pid_ctrl (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
