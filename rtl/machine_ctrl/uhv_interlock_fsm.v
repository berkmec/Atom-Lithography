// uhv_interlock_fsm.v - True 1oo2D Dual-Channel Fail-Safe UHV & Facility Interlock FSM
// BOM Traceability: S5.5-04, S7.4-04, S7.SAFETY-01, S7.SAFETY-02, S7.SAFETY-03,
//                   S7.SAFETY-04, S7.SAFETY-05, S7.SAFETY-06
// Target Clock    : 100.0 MHz (10.0 ns period)
//
// EPISTEMIC NOTICE (HARDWIRED INTO READ-ONLY CSR):
//   CERTIFIED                  = 1'b0 (NOT IEC 61508 / SEMI S2 certified!)
//   DESIGN_ONLY_NOT_CERTIFIED  = 1'b1 (Preliminary M0/M1 RTL reference only)
//
// Fail-Safe 1oo2D Sensor Channels (active-HIGH = HEALTHY, 0 = TRIP / OPEN-CIRCUIT FAULT):
//   Bit 0 : UHV_PRESSURE_OK  (Ion gauge < 1e-8 Torr; closes UHV gate valve & blanks beam)
//   Bit 1 : LASER_DOOR_OK    (Class-4 808 nm enclosure & OD>=8 shroud guard switches)
//   Bit 2 : ODH_O2_OK        (Wall O2 monitor >= 19.5% vol; 0 when O2 < 19.5%)
//   Bit 3 : PH3_L1_OK        (PH3 Level-1 sensor < 0.02 ppm gas cabinet alarm)
//   Bit 4 : PH3_L2_OK        (PH3 Level-2 sensor < 0.30 ppm emergency isolation)
//   Bit 5 : HV_FAULT_OK      (HV supply / arc / crowbar feedback healthy)
//   Bit 6 : QUENCH_OK        (1.5 T magnet quench detector & cryo relief healthy)
//   Bit 7 : ESTOP_OK         (4x E-Stop mushroom loop healthy)
//
// Safety Mechanisms:
//   1. True 1oo2 Voting: either channel A or channel B dropping LOW trips ALL outputs
//      to de-energized safe state (0) immediately (<= 2 clocks = <= 20 ns @ 100 MHz,
//      strictly < 1 us blanker budget).
//   2. Diagnostic Cross-Channel Discrepancy Fault ('D' in 1oo2D): if ch_a != ch_b
//      persists beyond programmable `discrep_win_cycles`, latches `discrep_fault` and
//      exact channel bitmask `discrep_ch_latched[7:0]`.
//   3. Hardware Watchdog Heartbeat Monitor: trips immediately if `wdt_kick` is not
//      pulsed within `wdt_timeout_cycles` while `wdt_en` is asserted.
//   4. De-Energize-To-Trip Active-HIGH Safe Enables: reset to 0, drop LOW immediately on
//      any fault.
//   5. Staged Safe-Dwell Unlock: leaving FAULT_LATCHED requires ALL inputs healthy
//      AND simultaneous dual-channel reset (`reset_cmd_a && reset_cmd_b`), followed by
//      continuous healthy dwell for `dwell_cycles` before permitting `ST_ARMED -> ST_RUN`.
//
// Synthesis Hygiene: ZERO latches, ZERO combinational '/', ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module uhv_interlock_fsm #(
    parameter [15:0] DEFAULT_DISCREP_WIN  = 16'd100,        // 1.0 us @ 100 MHz
    parameter [31:0] DEFAULT_WDT_TIMEOUT  = 32'd10_000_000, // 100 ms @ 100 MHz
    parameter [31:0] DEFAULT_DWELL_CYCLES = 32'd200_000_000 // 2.0 s  @ 100 MHz
) (
    input  wire        clk,
    input  wire        rst_n,

    // Dual-channel 1oo2D fail-safe inputs (1 = HEALTHY, 0 = FAULT/OPEN-WIRE)
    input  wire [7:0]  ch_a_ok,
    input  wire [7:0]  ch_b_ok,

    // Control & reset inputs
    input  wire        run_enable_cmd,
    input  wire        sw_estop,
    input  wire        reset_cmd_a,
    input  wire        reset_cmd_b,
    input  wire        wdt_en,
    input  wire        wdt_kick,
    input  wire [5:0]  subsys_en_mask, // {magnet, ph3, uhv_valve, hv, laser, blanker}

    // Programmable timing thresholds (0 selects default parameter value)
    input  wire [15:0] cfg_discrep_win,
    input  wire [31:0] cfg_wdt_timeout,
    input  wire [31:0] cfg_dwell_cycles,

    // De-energize-to-trip active-HIGH safe-enable outputs (0 = SAFE/TRIPPED)
    output wire        safe_blanker_en,
    output wire        safe_laser_en,
    output wire        safe_hv_en,
    output wire        safe_uhv_valve_en,
    output wire        safe_ph3_valve_en,
    output wire        safe_magnet_en,

    // Hardwired active-HIGH trip broadcast (1 = TRIPPED / NOT IN RUN)
    output wire        interlock_trip_out,

    // Diagnostic & Telemetry outputs
    output reg  [2:0]  fsm_state,
    output reg  [7:0]  sensor_fault_latched,
    output reg         discrep_fault_latched,
    output reg  [7:0]  discrep_ch_latched,
    output reg         wdt_fault_latched,
    output reg         sw_estop_latched,
    output reg  [3:0]  first_fault_code,
    output reg  [15:0] trip_counter,
    output wire [7:0]  ch_a_sync_out,
    output wire [7:0]  ch_b_sync_out,
    output wire [7:0]  discrep_live_out,

    // Explicit Read-Only Epistemic CSR Status
    output wire        status_certified,
    output wire        status_design_only_not_certified,
    output wire [31:0] epistemic_csr_word
);
    // FSM state encoding
    localparam [2:0] ST_SAFE_BOOT     = 3'd0;
    localparam [2:0] ST_FAULT_LATCHED = 3'd1;
    localparam [2:0] ST_SAFE_DWELL    = 3'd2;
    localparam [2:0] ST_ARMED         = 3'd3;
    localparam [2:0] ST_RUN           = 3'd4;

    // First-fault diagnostic codes
    localparam [3:0] FC_NONE         = 4'd0;
    localparam [3:0] FC_UHV_PRESSURE = 4'd1;
    localparam [3:0] FC_LASER_DOOR   = 4'd2;
    localparam [3:0] FC_ODH_O2       = 4'd3;
    localparam [3:0] FC_PH3_L1       = 4'd4;
    localparam [3:0] FC_PH3_L2       = 4'd5;
    localparam [3:0] FC_HV_FAULT     = 4'd6;
    localparam [3:0] FC_QUENCH       = 4'd7;
    localparam [3:0] FC_ESTOP        = 4'd8;
    localparam [3:0] FC_DISCREPANCY  = 4'd9;
    localparam [3:0] FC_WATCHDOG     = 4'd10;
    localparam [3:0] FC_SW_ESTOP     = 4'd11;

    // Hardwired read-only epistemic status bits (never modifiable at runtime)
    assign status_certified                 = 1'b0;
    assign status_design_only_not_certified = 1'b1;
    // [31:16]=0xD001 (DESIGN_ONLY v0.01), [15:8]=0x53 ('S'), [3]=1oo2D, [2]=no_lab, [1]=DESIGN_ONLY, [0]=CERTIFIED(0)
    assign epistemic_csr_word               = 32'hD001_530E;

    // 1-stage synchronous input capture + fast raw trip monitor
    // Gives clean synchronous voting with 1-cycle FSM reaction + 0-cycle output gate
    // (total trip-to-output drop <= 1 clock = 10 ns @ 100 MHz, strictly < 1 us!).
    reg [7:0] ch_a_s1;
    reg [7:0] ch_b_s1;

    assign ch_a_sync_out    = ch_a_s1;
    assign ch_b_sync_out    = ch_b_s1;
    assign discrep_live_out = ch_a_s1 ^ ch_b_s1;

    // Effective thresholds
    wire [15:0] eff_discrep_win  = (cfg_discrep_win  == 16'd0) ? DEFAULT_DISCREP_WIN  : cfg_discrep_win;
    wire [31:0] eff_wdt_timeout  = (cfg_wdt_timeout  == 32'd0) ? DEFAULT_WDT_TIMEOUT  : cfg_wdt_timeout;
    wire [31:0] eff_dwell_cycles = (cfg_dwell_cycles == 32'd0) ? DEFAULT_DWELL_CYCLES : cfg_dwell_cycles;

    // 1oo2 channel fault vector (1 = channel tripped on A or B)
    wire [7:0] ch_fault_sync = (~ch_a_s1) | (~ch_b_s1);
    wire       any_ch_fault_sync = |ch_fault_sync;
    wire       any_ch_fault_raw  = (~(&ch_a_ok)) | (~(&ch_b_ok));
    wire       all_inputs_healthy = (&ch_a_s1) && (&ch_b_s1) && (&ch_a_ok) && (&ch_b_ok) && (~sw_estop);

    // Discrepancy & Watchdog & Dwell timers
    reg [15:0] discrep_cnt;
    reg [31:0] wdt_cnt;
    reg [31:0] dwell_cnt;
    reg        wdt_expired_now;

    // Combinational priority encoder for first-out root-cause fault code
    reg [3:0] cur_fault_code;
    always @(*) begin
        if (sw_estop)              cur_fault_code = FC_SW_ESTOP;
        else if (ch_fault_sync[7]) cur_fault_code = FC_ESTOP;
        else if (ch_fault_sync[4]) cur_fault_code = FC_PH3_L2;
        else if (ch_fault_sync[2]) cur_fault_code = FC_ODH_O2;
        else if (ch_fault_sync[6]) cur_fault_code = FC_QUENCH;
        else if (ch_fault_sync[5]) cur_fault_code = FC_HV_FAULT;
        else if (ch_fault_sync[1]) cur_fault_code = FC_LASER_DOOR;
        else if (ch_fault_sync[0]) cur_fault_code = FC_UHV_PRESSURE;
        else if (ch_fault_sync[3]) cur_fault_code = FC_PH3_L1;
        else if (wdt_expired_now)  cur_fault_code = FC_WATCHDOG;
        else                       cur_fault_code = FC_DISCREPANCY;
    end

    // Registered safe-enable mask + hardwired raw fail-safe gate for instantaneous de-energize
    reg [5:0] r_safe_en;
    wire      live_fault_now = any_ch_fault_raw | any_ch_fault_sync | sw_estop |
                               wdt_fault_latched | discrep_fault_latched | sw_estop_latched |
                               (|sensor_fault_latched);

    wire [5:0] gated_safe_en = live_fault_now ? 6'b000000 : r_safe_en;

    assign safe_blanker_en    = gated_safe_en[0];
    assign safe_laser_en      = gated_safe_en[1];
    assign safe_hv_en         = gated_safe_en[2];
    assign safe_uhv_valve_en  = gated_safe_en[3];
    assign safe_ph3_valve_en  = gated_safe_en[4];
    assign safe_magnet_en     = gated_safe_en[5];
    assign interlock_trip_out = live_fault_now | (fsm_state != ST_RUN);

    // Watchdog expiry evaluation (combinational lookahead for 1-cycle trip)
    always @(*) begin
        if (wdt_en && !wdt_kick && (wdt_cnt >= (eff_wdt_timeout - 32'd1))) begin
            wdt_expired_now = 1'b1;
        end else begin
            wdt_expired_now = 1'b0;
        end
    end

    wire discrep_active      = |(ch_a_s1 ^ ch_b_s1);
    wire discrep_trip_now    = discrep_active && (discrep_cnt >= (eff_discrep_win - 16'd1));
    wire dual_reset_valid    = reset_cmd_a && reset_cmd_b && all_inputs_healthy && !discrep_active;
    wire any_trip_trigger    = any_ch_fault_sync || sw_estop || wdt_expired_now || discrep_trip_now;

    always @(posedge clk) begin
        if (!rst_n) begin
            ch_a_s1               <= 8'h00; // fail-safe reset state = tripped
            ch_b_s1               <= 8'h00;
            fsm_state             <= ST_SAFE_BOOT;
            sensor_fault_latched  <= 8'h00;
            discrep_fault_latched <= 1'b0;
            discrep_ch_latched    <= 8'h00;
            wdt_fault_latched     <= 1'b0;
            sw_estop_latched      <= 1'b0;
            first_fault_code      <= FC_NONE;
            trip_counter          <= 16'd0;
            discrep_cnt           <= 16'd0;
            wdt_cnt               <= 32'd0;
            dwell_cnt             <= 32'd0;
            r_safe_en             <= 6'b000000;
        end else begin
            // Capture redundant sensor channels every cycle
            ch_a_s1 <= ch_a_ok;
            ch_b_s1 <= ch_b_ok;

            // Cross-channel 1oo2D discrepancy debounce monitor
            if (discrep_active) begin
                if (discrep_cnt < eff_discrep_win) begin
                    discrep_cnt <= discrep_cnt + 16'd1;
                end
                if (discrep_trip_now) begin
                    discrep_fault_latched <= 1'b1;
                    discrep_ch_latched    <= discrep_ch_latched | (ch_a_s1 ^ ch_b_s1);
                end
            end else begin
                discrep_cnt <= 16'd0;
            end

            // Hardware watchdog counter
            if (!wdt_en || wdt_kick || (fsm_state == ST_FAULT_LATCHED) || (fsm_state == ST_SAFE_BOOT)) begin
                wdt_cnt <= 32'd0;
            end else if (wdt_expired_now) begin
                wdt_fault_latched <= 1'b1;
                wdt_cnt           <= 32'd0;
            end else begin
                wdt_cnt <= wdt_cnt + 32'd1;
            end

            // Latch sensor / sw_estop faults whenever they occur
            if (any_ch_fault_sync && (fsm_state != ST_SAFE_BOOT)) begin
                sensor_fault_latched <= sensor_fault_latched | ch_fault_sync;
            end
            if (sw_estop) begin
                sw_estop_latched <= 1'b1;
            end

            // Record first-out fault code if none latched yet
            if ((first_fault_code == FC_NONE) && any_trip_trigger && (fsm_state != ST_SAFE_BOOT)) begin
                first_fault_code <= cur_fault_code;
            end

            // Main Fail-Safe Interlock FSM
            case (fsm_state)
                ST_SAFE_BOOT: begin
                    r_safe_en <= 6'b000000;
                    dwell_cnt <= 32'd0;
                    // Wait 1+ cycles after reset for ch_a_s1/ch_b_s1 capture; require explicit dual-reset
                    if (dual_reset_valid) begin
                        sensor_fault_latched  <= 8'h00;
                        discrep_fault_latched <= 1'b0;
                        discrep_ch_latched    <= 8'h00;
                        wdt_fault_latched     <= 1'b0;
                        sw_estop_latched      <= 1'b0;
                        first_fault_code      <= FC_NONE;
                        dwell_cnt             <= 32'd0;
                        fsm_state             <= ST_SAFE_DWELL;
                    end else if (any_ch_fault_sync || sw_estop) begin
                        sensor_fault_latched <= ch_fault_sync;
                        sw_estop_latched     <= sw_estop;
                        first_fault_code     <= cur_fault_code;
                        fsm_state            <= ST_FAULT_LATCHED;
                    end
                end

                ST_FAULT_LATCHED: begin
                    r_safe_en <= 6'b000000;
                    dwell_cnt <= 32'd0;
                    // Unlock ONLY when ALL 16 sensor channels healthy, no discrepancy,
                    // no sw_estop, AND dual-channel reset (A && B) asserted simultaneously.
                    if (dual_reset_valid) begin
                        sensor_fault_latched  <= 8'h00;
                        discrep_fault_latched <= 1'b0;
                        discrep_ch_latched    <= 8'h00;
                        wdt_fault_latched     <= 1'b0;
                        sw_estop_latched      <= 1'b0;
                        first_fault_code      <= FC_NONE;
                        dwell_cnt             <= 32'd0;
                        fsm_state             <= ST_SAFE_DWELL;
                    end
                end

                ST_SAFE_DWELL: begin
                    r_safe_en <= 6'b000000;
                    if (any_trip_trigger || !all_inputs_healthy) begin
                        trip_counter <= trip_counter + 16'd1;
                        dwell_cnt    <= 32'd0;
                        fsm_state    <= ST_FAULT_LATCHED;
                    end else if (dwell_cnt >= (eff_dwell_cycles - 32'd1)) begin
                        dwell_cnt <= 32'd0;
                        fsm_state <= ST_ARMED;
                    end else begin
                        dwell_cnt <= dwell_cnt + 32'd1;
                    end
                end

                ST_ARMED: begin
                    if (any_trip_trigger || !all_inputs_healthy) begin
                        r_safe_en    <= 6'b000000;
                        trip_counter <= trip_counter + 16'd1;
                        fsm_state    <= ST_FAULT_LATCHED;
                    end else if (run_enable_cmd) begin
                        r_safe_en <= subsys_en_mask;
                        fsm_state <= ST_RUN;
                    end else begin
                        // In ARMED, keep hazardous actuators disabled (de-energized)
                        r_safe_en <= 6'b000000;
                    end
                end

                ST_RUN: begin
                    if (any_trip_trigger || !all_inputs_healthy) begin
                        r_safe_en    <= 6'b000000;
                        trip_counter <= trip_counter + 16'd1;
                        fsm_state    <= ST_FAULT_LATCHED;
                    end else if (!run_enable_cmd) begin
                        r_safe_en <= 6'b000000;
                        fsm_state <= ST_ARMED;
                    end else begin
                        r_safe_en <= subsys_en_mask;
                    end
                end

                default: begin
                    r_safe_en <= 6'b000000;
                    fsm_state <= ST_FAULT_LATCHED;
                end
            endcase
        end
    end
endmodule
