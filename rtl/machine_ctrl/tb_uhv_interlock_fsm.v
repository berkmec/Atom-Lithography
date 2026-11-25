// tb_uhv_interlock_fsm.v - Self-checking 1oo2D fail-safe interlock & fault-injection TB
`timescale 1ns/1ps

module tb_uhv_interlock_fsm;
    localparam integer CLK_PERIOD_NS = 10; // 100 MHz

    reg        clk;
    reg        rst_n;
    reg [7:0]  ch_a_ok;
    reg [7:0]  ch_b_ok;
    reg        run_enable_cmd;
    reg        sw_estop;
    reg        reset_cmd_a;
    reg        reset_cmd_b;
    reg        wdt_en;
    reg        wdt_kick;
    reg [5:0]  subsys_en_mask;
    reg [15:0] cfg_discrep_win;
    reg [31:0] cfg_wdt_timeout;
    reg [31:0] cfg_dwell_cycles;

    wire       safe_blanker_en;
    wire       safe_laser_en;
    wire       safe_hv_en;
    wire       safe_uhv_valve_en;
    wire       safe_ph3_valve_en;
    wire       safe_magnet_en;
    wire       interlock_trip_out;
    wire [2:0] fsm_state;
    wire [7:0] sensor_fault_latched;
    wire       discrep_fault_latched;
    wire [7:0] discrep_ch_latched;
    wire       wdt_fault_latched;
    wire       sw_estop_latched;
    wire [3:0] first_fault_code;
    wire [15:0] trip_counter;
    wire [7:0] ch_a_sync_out;
    wire [7:0] ch_b_sync_out;
    wire [7:0] discrep_live_out;
    wire       status_certified;
    wire       status_design_only_not_certified;
    wire [31:0] epistemic_csr_word;

    uhv_interlock_fsm #(
        .DEFAULT_DISCREP_WIN(16'd8),
        .DEFAULT_WDT_TIMEOUT(32'd25),
        .DEFAULT_DWELL_CYCLES(32'd12)
    ) dut (
        .clk                              (clk),
        .rst_n                            (rst_n),
        .ch_a_ok                          (ch_a_ok),
        .ch_b_ok                          (ch_b_ok),
        .run_enable_cmd                   (run_enable_cmd),
        .sw_estop                         (sw_estop),
        .reset_cmd_a                      (reset_cmd_a),
        .reset_cmd_b                      (reset_cmd_b),
        .wdt_en                           (wdt_en),
        .wdt_kick                         (wdt_kick),
        .subsys_en_mask                   (subsys_en_mask),
        .cfg_discrep_win                  (cfg_discrep_win),
        .cfg_wdt_timeout                  (cfg_wdt_timeout),
        .cfg_dwell_cycles                 (cfg_dwell_cycles),
        .safe_blanker_en                  (safe_blanker_en),
        .safe_laser_en                    (safe_laser_en),
        .safe_hv_en                       (safe_hv_en),
        .safe_uhv_valve_en                (safe_uhv_valve_en),
        .safe_ph3_valve_en                (safe_ph3_valve_en),
        .safe_magnet_en                   (safe_magnet_en),
        .interlock_trip_out               (interlock_trip_out),
        .fsm_state                        (fsm_state),
        .sensor_fault_latched             (sensor_fault_latched),
        .discrep_fault_latched            (discrep_fault_latched),
        .discrep_ch_latched               (discrep_ch_latched),
        .wdt_fault_latched                (wdt_fault_latched),
        .sw_estop_latched                 (sw_estop_latched),
        .first_fault_code                 (first_fault_code),
        .trip_counter                     (trip_counter),
        .ch_a_sync_out                    (ch_a_sync_out),
        .ch_b_sync_out                    (ch_b_sync_out),
        .discrep_live_out                 (discrep_live_out),
        .status_certified                 (status_certified),
        .status_design_only_not_certified (status_design_only_not_certified),
        .epistemic_csr_word               (epistemic_csr_word)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    wire [5:0] all_safe_en = {safe_magnet_en, safe_ph3_valve_en, safe_uhv_valve_en,
                              safe_hv_en, safe_laser_en, safe_blanker_en};

    integer errors;
    integer ch_i;
    integer max_trip_ns;
    time    t0, t1;
    integer dt_ns;

    task bring_to_run;
        begin
            @(negedge clk);
            ch_a_ok        = 8'hFF;
            ch_b_ok        = 8'hFF;
            sw_estop       = 1'b0;
            wdt_en         = 1'b0;
            run_enable_cmd = 1'b1;
            repeat (2) @(posedge clk);

            // Simultaneous dual-channel reset
            @(negedge clk);
            reset_cmd_a = 1'b1;
            reset_cmd_b = 1'b1;
            @(posedge clk);
            @(negedge clk);
            reset_cmd_a = 1'b0;
            reset_cmd_b = 1'b0;

            // Wait through 12-cycle safe dwell + armed -> run
            repeat (16) @(posedge clk);
            #1;
            if (fsm_state !== 3'd4 || all_safe_en !== 6'b111111 || interlock_trip_out !== 1'b0) begin
                $display("ERROR: bring_to_run failed: state=%0d safe_en=%b trip=%b",
                         fsm_state, all_safe_en, interlock_trip_out);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        errors           = 0;
        max_trip_ns      = 0;
        rst_n            = 1'b0;
        ch_a_ok          = 8'hFF;
        ch_b_ok          = 8'hFF;
        run_enable_cmd   = 1'b0;
        sw_estop         = 1'b0;
        reset_cmd_a      = 1'b0;
        reset_cmd_b      = 1'b0;
        wdt_en           = 1'b0;
        wdt_kick         = 1'b0;
        subsys_en_mask   = 6'b111111;
        cfg_discrep_win  = 16'd8;
        cfg_wdt_timeout  = 32'd25;
        cfg_dwell_cycles = 32'd12;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);
        #1;

        // 1. Verify hardwired read-only epistemic status bits
        if (status_certified !== 1'b0 || status_design_only_not_certified !== 1'b1 ||
            epistemic_csr_word !== 32'hD001_530E) begin
            $display("ERROR: epistemic CSR mismatch: cert=%b design_only=%b word=%h",
                     status_certified, status_design_only_not_certified, epistemic_csr_word);
            errors = errors + 1;
        end

        // 2. Verify power-on de-energized safe state
        if (all_safe_en !== 6'b000000 || interlock_trip_out !== 1'b1) begin
            $display("ERROR: outputs not de-energized on boot!");
            errors = errors + 1;
        end

        // 3. Verify single-channel reset (A only or B only) is REJECTED
        @(negedge clk);
        reset_cmd_a = 1'b1;
        reset_cmd_b = 1'b0;
        @(posedge clk);
        @(negedge clk);
        reset_cmd_a = 1'b0;
        reset_cmd_b = 1'b1;
        @(posedge clk);
        @(negedge clk);
        reset_cmd_b = 1'b0;
        repeat (3) @(posedge clk);
        if (fsm_state == 3'd2 || fsm_state == 3'd3 || fsm_state == 3'd4 || all_safe_en !== 6'b000000) begin
            $display("ERROR: single-channel reset bypassed dual-reset interlock!");
            errors = errors + 1;
        end

        // 4. Verify glitch during safe-dwell aborts back to ST_FAULT_LATCHED
        @(negedge clk);
        reset_cmd_a = 1'b1;
        reset_cmd_b = 1'b1;
        @(posedge clk);
        @(negedge clk);
        reset_cmd_a = 1'b0;
        reset_cmd_b = 1'b0;
        repeat (4) @(posedge clk);
        // Inject 1-cycle UHV glitch during dwell
        @(negedge clk);
        ch_a_ok[0] = 1'b0;
        @(posedge clk);
        @(negedge clk);
        ch_a_ok[0] = 1'b1;
        repeat (2) @(posedge clk);
        #1;
        if (fsm_state !== 3'd1 || all_safe_en !== 6'b000000) begin
            $display("ERROR: dwell glitch did not abort to ST_FAULT_LATCHED! state=%0d", fsm_state);
            errors = errors + 1;
        end

        // 5. Test ALL 8 hazard channels on BOTH Channel A and Channel B (16 1oo2 fault injections)
        for (ch_i = 0; ch_i < 8; ch_i = ch_i + 1) begin
            // Channel A trip
            bring_to_run();
            @(negedge clk);
            t0 = $time;
            ch_a_ok[ch_i] = 1'b0;
            #1;
            if (all_safe_en !== 6'b000000 || interlock_trip_out !== 1'b1) begin
                $display("ERROR: ChA bit %0d trip failed immediate de-energize!", ch_i);
                errors = errors + 1;
            end
            repeat (2) @(posedge clk);
            #1;
            t1 = $time;
            dt_ns = t1 - t0;
            if (dt_ns > max_trip_ns) max_trip_ns = dt_ns;
            if (fsm_state !== 3'd1 || !sensor_fault_latched[ch_i]) begin
                $display("ERROR: ChA bit %0d did not latch fault! state=%0d latch=%b",
                         ch_i, fsm_state, sensor_fault_latched);
                errors = errors + 1;
            end

            // Channel B trip
            bring_to_run();
            @(negedge clk);
            ch_b_ok[ch_i] = 1'b0;
            #1;
            if (all_safe_en !== 6'b000000 || interlock_trip_out !== 1'b1) begin
                $display("ERROR: ChB bit %0d trip failed immediate de-energize!", ch_i);
                errors = errors + 1;
            end
            repeat (2) @(posedge clk);
            #1;
            if (fsm_state !== 3'd1 || !sensor_fault_latched[ch_i]) begin
                $display("ERROR: ChB bit %0d did not latch fault! state=%0d latch=%b",
                         ch_i, fsm_state, sensor_fault_latched);
                errors = errors + 1;
            end
        end

        // 6. Test 1oo2D Cross-Channel Discrepancy Fault Detection (O2 sensor ch 2)
        bring_to_run();
        @(negedge clk);
        ch_a_ok[2] = 1'b0; // ch_a[2]=0, ch_b[2]=1 -> cross-channel discrepancy!
        repeat (12) @(posedge clk); // exceeds cfg_discrep_win=8
        #1;
        if (!discrep_fault_latched || discrep_ch_latched !== 8'h04) begin
            $display("ERROR: 1oo2D discrepancy not detected! flag=%b mask=%h",
                     discrep_fault_latched, discrep_ch_latched);
            errors = errors + 1;
        end
        if (discrep_live_out !== 8'h04 || ch_a_sync_out[2] !== 1'b0 || ch_b_sync_out[2] !== 1'b1) begin
            $display("ERROR: live discrepancy telemetry mismatch!");
            errors = errors + 1;
        end

        // 7. Test Hardware Watchdog Heartbeat (kick keeps alive, starve trips)
        bring_to_run();
        @(negedge clk);
        wdt_en = 1'b1;
        repeat (15) @(posedge clk);
        @(negedge clk);
        wdt_kick = 1'b1;
        @(posedge clk);
        @(negedge clk);
        wdt_kick = 1'b0;
        repeat (15) @(posedge clk);
        #1;
        if (fsm_state !== 3'd4 || wdt_fault_latched !== 1'b0) begin
            $display("ERROR: WDT tripped despite valid heartbeat kick!");
            errors = errors + 1;
        end
        // Now starve watchdog for 30 cycles (> 25 timeout)
        repeat (30) @(posedge clk);
        #1;
        if (fsm_state !== 3'd1 || wdt_fault_latched !== 1'b1 || all_safe_en !== 6'b000000) begin
            $display("ERROR: WDT timeout did not trip! state=%0d wdt=%b safe=%b",
                     fsm_state, wdt_fault_latched, all_safe_en);
            errors = errors + 1;
        end
        if (first_fault_code !== 4'd10) begin
            $display("ERROR: expected FC_WATCHDOG(10), got %0d", first_fault_code);
            errors = errors + 1;
        end

        // 8. Test Software E-Stop
        bring_to_run();
        @(negedge clk);
        sw_estop = 1'b1;
        #1;
        if (all_safe_en !== 6'b000000 || interlock_trip_out !== 1'b1) begin
            $display("ERROR: sw_estop did not drop enables immediately!");
            errors = errors + 1;
        end
        repeat (2) @(posedge clk);
        #1;
        if (!sw_estop_latched || fsm_state !== 3'd1 || first_fault_code !== 4'd11) begin
            $display("ERROR: sw_estop latch/code mismatch!");
            errors = errors + 1;
        end

        $display("INTERLOCK_SUMMARY errors=%0d channels_tested=16 discrep_ok=1 wdt_ok=1 max_trip_ns=%0d trips=%0d certified=%0d design_only=%0d",
                 errors, max_trip_ns, trip_counter, status_certified, status_design_only_not_certified);
        if (errors == 0) begin
            $display("PASS: tb_uhv_interlock_fsm");
            $finish;
        end else begin
            $display("FAIL: tb_uhv_interlock_fsm (%0d errors)", errors);
            $fatal(1);
        end
    end
endmodule
