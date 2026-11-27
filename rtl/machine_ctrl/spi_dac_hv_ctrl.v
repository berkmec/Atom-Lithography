// spi_dac_hv_ctrl.v - Synchronized 8-Channel 20-Bit Precision SPI DAC HV Controller
// BOM Traceability: S1.2-03, S1.3-03, S2.3-04, S3.2-02, S6.7-02, S6.10-03, S6.10-04
// Target Clock    : 100.0 MHz (10.0 ns period)
//
// Features:
//   - 8-channel x 20-bit DAC shadow register bank (HV electrostatic lens, Stark bias,
//     detector guard ring, cryo crossbar gates)
//   - 24-bit MSB-first SPI Mode-0 (CPOL=0, CPHA=0) frame:
//       frame[23]    = 1'b0 (Write command)
//       frame[22:20] = channel address [2:0] (0..7)
//       frame[19:0]  = 20-bit DAC code (20'h00000 = safe zero / crowbar code)
//   - Hardware-enforced AD5791 timing compliance (OBS-144):
//       * f_SCLK = f_sys / (2 * eff_div): DEFAULT_SCLK_DIV=4 -> 12.5 MHz @ 100 MHz
//       * Hardware SCLK divider floor MIN_SCLK_DIV=2 -> max 25.0 MHz (<= 35 MHz 3.3V spec)
//       * Dedicated minimum pulse timer MIN_PULSE_CYCLES=3 (>= 30 ns >= 20 ns AD5791
//         minimum t_CS_HIGH and t_LDAC pulse width even if cfg_sclk_div=1!)
//   - Built-in 2-FF async-assert / sync-deassert reset synchronizer (`rst_sync_n`).
//   - Hard-wired `hv_safe_clamp` zero-override: immediate `hv_clr_n=0` + 8-ch 20'h00000 burst.
//
// Synthesis Hygiene: ZERO latches, ZERO combinational '/', ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module spi_dac_hv_ctrl #(
    parameter [15:0] DEFAULT_SCLK_DIV = 16'd4, // 12.5 MHz SCLK @ 100 MHz sys_clk (100/(2*4))
    parameter [15:0] MIN_SCLK_DIV     = 16'd2, // Max 25.0 MHz SCLK (<= 35 MHz AD5791 3.3V limit)
    parameter [15:0] MIN_PULSE_CYCLES = 16'd3  // >= 30 ns t_CS_HIGH / t_LDAC @ 100 MHz (>= 20 ns)
) (
    input  wire        clk,
    input  wire        rst_n,

    // Hard-wired safety clamp from uhv_interlock_fsm (active-HIGH = FORCE ZERO HV)
    input  wire        hv_safe_clamp,

    // Host CSR channel write/read interface
    input  wire        ch_wr_en,
    input  wire [2:0]  ch_wr_addr,
    input  wire [19:0] ch_wr_data,
    input  wire [2:0]  ch_rd_addr,
    output wire [19:0] ch_rd_data,

    // Transfer control
    input  wire        start_update,
    input  wire        update_all,
    input  wire [7:0]  ch_update_mask,
    input  wire [15:0] cfg_sclk_div,

    // Physical SPI + Simultaneous LDAC + Async Clear outputs
    output reg         spi_cs_n,
    output reg         spi_sclk,
    output reg         spi_mosi,
    output reg         spi_ldac_n,
    output wire        hv_clr_n,

    // Telemetry & status outputs
    output wire        busy,
    output reg         done_sticky,
    output reg         clamp_zero_seq_done,
    output reg  [3:0]  cur_ch_out,
    output reg  [23:0] last_tx_frame
);
    // FSM states
    localparam [2:0] ST_IDLE       = 3'd0;
    localparam [2:0] ST_FIND_NEXT  = 3'd1;
    localparam [2:0] ST_CS_SETUP   = 3'd2;
    localparam [2:0] ST_SHIFT_LOW  = 3'd3;
    localparam [2:0] ST_SHIFT_HIGH = 3'd4;
    localparam [2:0] ST_CS_HOLD    = 3'd5;
    localparam [2:0] ST_LDAC_PULSE = 3'd6;

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

    // 8 x 20-bit channel code registers
    reg [19:0] dac_code [0:7];

    // Effective SCLK divider with hardware floor + minimum t_CS_HIGH / t_LDAC pulse timer
    wire [15:0] raw_div       = (cfg_sclk_div == 16'd0) ? DEFAULT_SCLK_DIV : cfg_sclk_div;
    wire [15:0] eff_div       = (raw_div < MIN_SCLK_DIV) ? MIN_SCLK_DIV : raw_div;
    wire [15:0] div_limit     = eff_div - 16'd1;
    wire [15:0] min_pulse_lim = (MIN_PULSE_CYCLES > 16'd1) ? (MIN_PULSE_CYCLES - 16'd1) : 16'd0;
    wire [15:0] pulse_limit   = (div_limit < min_pulse_lim) ? min_pulse_lim : div_limit;

    // Internal FSM registers
    reg [2:0]  state;
    reg [7:0]  pending_mask;
    reg [4:0]  bit_cnt;       // 0..23
    reg [23:0] shift_reg;
    reg [15:0] div_cnt;
    reg        clamp_mode;
    reg        hv_clamp_prev;

    // Immediate hardware async clear pin (active-LOW = CLEAR DAC OUTPUTS TO 0 V)
    assign hv_clr_n   = ~hv_safe_clamp;
    assign busy       = (state != ST_IDLE);
    assign ch_rd_data = dac_code[ch_rd_addr];

    // Combinational priority search for lowest-indexed channel set in pending_mask
    reg        found_ch;
    reg [2:0]  next_ch;
    always @(*) begin
        if (pending_mask[0])      begin found_ch = 1'b1; next_ch = 3'd0; end
        else if (pending_mask[1]) begin found_ch = 1'b1; next_ch = 3'd1; end
        else if (pending_mask[2]) begin found_ch = 1'b1; next_ch = 3'd2; end
        else if (pending_mask[3]) begin found_ch = 1'b1; next_ch = 3'd3; end
        else if (pending_mask[4]) begin found_ch = 1'b1; next_ch = 3'd4; end
        else if (pending_mask[5]) begin found_ch = 1'b1; next_ch = 3'd5; end
        else if (pending_mask[6]) begin found_ch = 1'b1; next_ch = 3'd6; end
        else if (pending_mask[7]) begin found_ch = 1'b1; next_ch = 3'd7; end
        else                      begin found_ch = 1'b0; next_ch = 3'd0; end
    end

    wire [7:0] start_mask = update_all ? 8'hFF : ch_update_mask;

    integer k;

    always @(posedge clk) begin
        if (!rst_sync_n) begin
            state               <= ST_IDLE;
            pending_mask        <= 8'h00;
            bit_cnt             <= 5'd0;
            shift_reg           <= 24'd0;
            div_cnt             <= 16'd0;
            clamp_mode          <= 1'b0;
            hv_clamp_prev       <= 1'b0;
            spi_cs_n            <= 1'b1;
            spi_sclk            <= 1'b0;
            spi_mosi            <= 1'b0;
            spi_ldac_n          <= 1'b1;
            done_sticky         <= 1'b0;
            clamp_zero_seq_done <= 1'b0;
            cur_ch_out          <= 4'd0;
            last_tx_frame       <= 24'd0;
            for (k = 0; k < 8; k = k + 1) begin
                dac_code[k] <= 20'd0;
            end
        end else begin
            hv_clamp_prev <= hv_safe_clamp;

            if (hv_safe_clamp) begin
                for (k = 0; k < 8; k = k + 1) begin
                    dac_code[k] <= 20'd0;
                end
            end else if (ch_wr_en) begin
                dac_code[ch_wr_addr] <= ch_wr_data;
            end

            if (hv_safe_clamp && (!hv_clamp_prev || (!clamp_mode && !clamp_zero_seq_done))) begin
                spi_cs_n            <= 1'b1;
                spi_sclk            <= 1'b0;
                spi_mosi            <= 1'b0;
                spi_ldac_n          <= 1'b1;
                clamp_mode          <= 1'b1;
                clamp_zero_seq_done <= 1'b0;
                done_sticky         <= 1'b0;
                pending_mask        <= 8'hFF;
                div_cnt             <= 16'd0;
                state               <= ST_FIND_NEXT;
            end else begin
                if (!hv_safe_clamp && hv_clamp_prev) begin
                    clamp_zero_seq_done <= 1'b0;
                end

                case (state)
                    ST_IDLE: begin
                        spi_cs_n   <= 1'b1;
                        spi_sclk   <= 1'b0;
                        spi_mosi   <= 1'b0;
                        spi_ldac_n <= 1'b1;
                        clamp_mode <= 1'b0;
                        if (!hv_safe_clamp && start_update && (start_mask != 8'h00)) begin
                            pending_mask <= start_mask;
                            done_sticky  <= 1'b0;
                            div_cnt      <= 16'd0;
                            state        <= ST_FIND_NEXT;
                        end
                    end

                    ST_FIND_NEXT: begin
                        spi_cs_n   <= 1'b1;
                        spi_sclk   <= 1'b0;
                        spi_ldac_n <= 1'b1;
                        if (found_ch) begin
                            cur_ch_out    <= {1'b0, next_ch};
                            pending_mask  <= pending_mask & (~(8'h01 << next_ch));
                            shift_reg     <= {1'b0, next_ch, (clamp_mode || hv_safe_clamp) ? 20'd0 : dac_code[next_ch]};
                            last_tx_frame <= {1'b0, next_ch, (clamp_mode || hv_safe_clamp) ? 20'd0 : dac_code[next_ch]};
                            bit_cnt       <= 5'd0;
                            div_cnt       <= 16'd0;
                            state         <= ST_CS_SETUP;
                        end else begin
                            spi_ldac_n <= 1'b0;
                            div_cnt    <= 16'd0;
                            state      <= ST_LDAC_PULSE;
                        end
                    end

                    ST_CS_SETUP: begin
                        spi_cs_n <= 1'b0;
                        spi_sclk <= 1'b0;
                        spi_mosi <= shift_reg[23];
                        if (div_cnt == div_limit) begin
                            div_cnt <= 16'd0;
                            state   <= ST_SHIFT_LOW;
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    ST_SHIFT_LOW: begin
                        spi_cs_n <= 1'b0;
                        spi_sclk <= 1'b0;
                        spi_mosi <= shift_reg[23];
                        if (div_cnt == div_limit) begin
                            div_cnt  <= 16'd0;
                            spi_sclk <= 1'b1;
                            state    <= ST_SHIFT_HIGH;
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    ST_SHIFT_HIGH: begin
                        spi_cs_n <= 1'b0;
                        spi_sclk <= 1'b1;
                        if (div_cnt == div_limit) begin
                            div_cnt  <= 16'd0;
                            spi_sclk <= 1'b0;
                            if (bit_cnt == 5'd23) begin
                                state <= ST_CS_HOLD;
                            end else begin
                                bit_cnt   <= bit_cnt + 5'd1;
                                shift_reg <= {shift_reg[22:0], 1'b0};
                                spi_mosi  <= shift_reg[22];
                                state     <= ST_SHIFT_LOW;
                            end
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    // Enforces hardware minimum t_CS_HIGH >= MIN_PULSE_CYCLES (30 ns >= 20 ns AD5791)
                    ST_CS_HOLD: begin
                        spi_cs_n <= 1'b1;
                        spi_sclk <= 1'b0;
                        spi_mosi <= 1'b0;
                        if (div_cnt >= pulse_limit) begin
                            div_cnt <= 16'd0;
                            state   <= ST_FIND_NEXT;
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    // Enforces hardware minimum t_LDAC >= MIN_PULSE_CYCLES (30 ns >= 20 ns AD5791)
                    ST_LDAC_PULSE: begin
                        spi_cs_n   <= 1'b1;
                        spi_sclk   <= 1'b0;
                        spi_ldac_n <= 1'b0;
                        if (div_cnt >= pulse_limit) begin
                            div_cnt     <= 16'd0;
                            spi_ldac_n  <= 1'b1;
                            done_sticky <= 1'b1;
                            if (clamp_mode) begin
                                clamp_zero_seq_done <= 1'b1;
                                clamp_mode          <= 1'b0;
                            end
                            state <= ST_IDLE;
                        end else begin
                            div_cnt <= div_cnt + 16'd1;
                        end
                    end

                    default: begin
                        spi_cs_n   <= 1'b1;
                        spi_sclk   <= 1'b0;
                        spi_ldac_n <= 1'b1;
                        state      <= ST_IDLE;
                    end
                endcase
            end
        end
    end
endmodule
