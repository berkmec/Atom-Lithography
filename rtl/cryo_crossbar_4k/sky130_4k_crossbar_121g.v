// sky130_4k_crossbar_121g.v - Synthesizable 4 K Cryo-CMOS 121-Gate Crossbar MUX Die RTL
// BOM Traceability: S6.10-03, S7.3-01 (SKY130_4K_CROSSBAR_121G_M0..M7, 8 dies x 121 = 968 gates)
// PCB Carrier Ref : hardware/pcb/cryo_cmos_4k_carrier/build_cryo_4k_carrier.py
//
// EPISTEMIC & CRYOGENIC CHARACTERIZATION NOTICE (OBS-143):
//   - TRL 2 (Synthesizable digital control/decode RTL only; NO 4 K cryogenic BSIM4/SKY130
//     PDK signoff, NO cryo tapeout, NO lab silicon measurement).
//   - At 4 K, SKY130 MOSFETs exhibit V_th shift (~+0.15..0.25 V) and kink effect
//     (kink_ratio up to 3.84 in results/exp32/nist_sky130.json). Standard 300 K TT/SS/FF
//     Liberty corners CANNOT sign off 4 K silicon without cryogenic PDK re-characterization!
//
// Architecture (121 gates per die; 8 daisy-chained dies M0..M7 = 968 DC gates for L=11 surface code):
//   - 16-bit SPI Mode-0 daisy-chain shift register (`spi_clk`, `spi_cs_n`, `spi_din` -> `spi_dout`):
//       [15:14] opcode:
//                 2'b00 = NOP
//                 2'b01 = SELECT_GATE  (1-of-121 crossbar mux select; addr 0..120 -> 11x11 row/col)
//                 2'b10 = REFRESH_CFG  (bit 0 = cyclic 121-gate S&H refresh enable, bits[10:4]=dwell)
//                 2'b11 = ALL_SAFE_ZERO (disconnect all 121 gates to safe ground clamp)
//       [13:11] bank/control flags ([13]=hold_clamp)
//       [10:4]  7-bit gate address (0..120; 121..127 rejected as OOB -> all switches OFF + fault_oob_addr)
//       [3:0]   DAC bus / bank tag [3:0]
//   - Strict mutual exclusion: at most ONE of 121 gates (`gate_sel[120:0]`) is ever asserted.
//   - Built-in 2-FF async-assert / sync-deassert reset synchronizer (`rst_sync_n`) and 2-FF CDC
//     synchronizers on `spi_clk`, `spi_cs_n`, `spi_din`.
//   - ZERO combinational '/' operators, ZERO latches, ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module sky130_4k_crossbar_121g #(
    parameter integer N_GATES = 121, // 11 x 11 crossbar per die (8 dies = 968 gates total)
    parameter integer N_ROWS  = 11,
    parameter integer N_COLS  = 11
) (
    input  wire               clk,          // Local refresh / digital control clock (e.g. 25 kHz..10 MHz)
    input  wire               rst_n,        // Active-LOW reset (2-FF synced internally)

    // Daisy-chained SPI Mode-0 control interface (matches cryo_cmos_4k_carrier 12-pin carrier)
    input  wire               spi_clk,
    input  wire               spi_cs_n,
    input  wire               spi_din,
    output wire               spi_dout,     // 16-bit shift-out to next die M(k+1)

    // Decoded 11x11 crossbar and 121-gate 1-hot analog switch controls
    output reg  [N_ROWS-1:0]  row_sel,
    output reg  [N_COLS-1:0]  col_sel,
    output reg  [N_GATES-1:0] gate_sel,

    // Status & telemetry outputs
    output reg  [6:0]         active_gate_addr,
    output reg  [3:0]         dac_bus_tag,
    output reg                gate_valid,
    output reg                refresh_en,
    output reg                safe_clamped,
    output reg                fault_oob_addr
);
    localparam [1:0] OP_NOP           = 2'b00;
    localparam [1:0] OP_SELECT_GATE   = 2'b01;
    localparam [1:0] OP_REFRESH_CFG   = 2'b10;
    localparam [1:0] OP_ALL_SAFE_ZERO = 2'b11;

    localparam [6:0] MAX_GATE_ADDR    = N_GATES[6:0] - 7'd1; // 7'd120

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

    // 2-FF CDC synchronizers on SPI lines crossing from 300 K FPGA to 4 K stage
    (* ASYNC_REG = "TRUE" *) reg sclk_s1, sclk_s2;
    (* ASYNC_REG = "TRUE" *) reg cs_n_s1, cs_n_s2;
    (* ASYNC_REG = "TRUE" *) reg din_s1,  din_s2;
    reg sclk_prev;
    reg cs_n_prev;

    wire sclk_rise = sclk_s2 & (~sclk_prev);
    wire cs_n_rise = cs_n_s2 & (~cs_n_prev);

    // 16-bit daisy-chain SPI shift register
    reg [15:0] shift_reg;
    assign spi_dout = shift_reg[15];

    // Refresh scan counter & programmable dwell
    reg [6:0]  ref_addr;
    reg [6:0]  ref_dwell_cfg;
    reg [6:0]  ref_dwell_cnt;
    reg        cmd_valid_hold;
    reg [6:0]  cmd_addr_hold;

    // Division-free 0..120 -> (row 0..10, col 0..10) decoder (ZERO combinational '/'!)
    reg [3:0] dec_row;
    reg [3:0] dec_col;
    reg [6:0] target_addr_c;
    reg       target_en_c;

    always @(*) begin
        target_en_c   = 1'b0;
        target_addr_c = 7'd0;
        if (!safe_clamped) begin
            if (refresh_en) begin
                target_en_c   = 1'b1;
                target_addr_c = ref_addr;
            end else if (cmd_valid_hold) begin
                target_en_c   = 1'b1;
                target_addr_c = cmd_addr_hold;
            end
        end

        // Exact lookup-based divide-by-11 for 0..120 (zero '/' operator)
        if      (target_addr_c < 7'd11)  begin dec_row = 4'd0;  dec_col = target_addr_c[3:0]; end
        else if (target_addr_c < 7'd22)  begin dec_row = 4'd1;  dec_col = target_addr_c[3:0] - 4'd11; end
        else if (target_addr_c < 7'd33)  begin dec_row = 4'd2;  dec_col = target_addr_c[3:0] - 4'd6;  end // 22 mod 16 = 6
        else if (target_addr_c < 7'd44)  begin dec_row = 4'd3;  dec_col = target_addr_c[3:0] - 4'd1;  end // 33 mod 16 = 1
        else if (target_addr_c < 7'd55)  begin dec_row = 4'd4;  dec_col = target_addr_c[3:0] - 4'd12; end // 44 mod 16 = 12
        else if (target_addr_c < 7'd66)  begin dec_row = 4'd5;  dec_col = target_addr_c[3:0] - 4'd7;  end // 55 mod 16 = 7
        else if (target_addr_c < 7'd77)  begin dec_row = 4'd6;  dec_col = target_addr_c[3:0] - 4'd2;  end // 66 mod 16 = 2
        else if (target_addr_c < 7'd88)  begin dec_row = 4'd7;  dec_col = target_addr_c[3:0] - 4'd13; end // 77 mod 16 = 13
        else if (target_addr_c < 7'd99)  begin dec_row = 4'd8;  dec_col = target_addr_c[3:0] - 4'd8;  end // 88 mod 16 = 8
        else if (target_addr_c < 7'd110) begin dec_row = 4'd9;  dec_col = target_addr_c[3:0] - 4'd3;  end // 99 mod 16 = 3
        else                             begin dec_row = 4'd10; dec_col = target_addr_c[3:0] - 4'd14; end // 110 mod 16 = 14
    end

    wire [1:0] rx_opcode = shift_reg[15:14];
    wire       rx_clamp  = shift_reg[13];
    wire [6:0] rx_addr   = shift_reg[10:4];
    wire [3:0] rx_tag    = shift_reg[3:0];

    wire _unused_ok = &{1'b0, shift_reg[12:11]};

    localparam [N_GATES-1:0] GATE_ONE = {{(N_GATES-1){1'b0}}, 1'b1};
    localparam [N_ROWS-1:0]  ROW_ONE  = {{(N_ROWS-1){1'b0}},  1'b1};
    localparam [N_COLS-1:0]  COL_ONE  = {{(N_COLS-1){1'b0}},  1'b1};

    always @(posedge clk) begin
        if (!rst_sync_n) begin
            sclk_s1          <= 1'b0;
            sclk_s2          <= 1'b0;
            sclk_prev        <= 1'b0;
            cs_n_s1          <= 1'b1;
            cs_n_s2          <= 1'b1;
            cs_n_prev        <= 1'b1;
            din_s1           <= 1'b0;
            din_s2           <= 1'b0;
            shift_reg        <= 16'd0;
            ref_addr         <= 7'd0;
            ref_dwell_cfg    <= 7'd1;
            ref_dwell_cnt    <= 7'd0;
            cmd_valid_hold   <= 1'b0;
            cmd_addr_hold    <= 7'd0;
            row_sel          <= {N_ROWS{1'b0}};
            col_sel          <= {N_COLS{1'b0}};
            gate_sel         <= {N_GATES{1'b0}};
            active_gate_addr <= 7'd0;
            dac_bus_tag      <= 4'd0;
            gate_valid       <= 1'b0;
            refresh_en       <= 1'b0;
            safe_clamped     <= 1'b1; // Fail-safe boot: all 121 gates disconnected!
            fault_oob_addr   <= 1'b0;
        end else begin
            // 2-FF CDC capture of SPI control bus
            sclk_s1   <= spi_clk;
            sclk_s2   <= sclk_s1;
            sclk_prev <= sclk_s2;
            cs_n_s1   <= spi_cs_n;
            cs_n_s2   <= cs_n_s1;
            cs_n_prev <= cs_n_s2;
            din_s1    <= spi_din;
            din_s2    <= din_s1;

            // Shift in MSB-first while CS_N is LOW
            if (!cs_n_s2 && sclk_rise) begin
                shift_reg <= {shift_reg[14:0], din_s2};
            end

            // Commit 16-bit command on CS_N rising edge (simultaneously across all 8 daisy-chained dies)
            if (cs_n_rise) begin
                case (rx_opcode)
                    OP_NOP: begin
                        // Preserve current state
                    end
                    OP_SELECT_GATE: begin
                        refresh_en  <= 1'b0;
                        dac_bus_tag <= rx_tag;
                        if (rx_clamp) begin
                            safe_clamped   <= 1'b1;
                            cmd_valid_hold <= 1'b0;
                            fault_oob_addr <= 1'b0;
                        end else if (rx_addr <= MAX_GATE_ADDR) begin
                            safe_clamped   <= 1'b0;
                            cmd_valid_hold <= 1'b1;
                            cmd_addr_hold  <= rx_addr;
                            fault_oob_addr <= 1'b0;
                        end else begin
                            // Out-of-bounds address (121..127) -> force ALL gates OFF & flag fault
                            safe_clamped   <= 1'b1;
                            cmd_valid_hold <= 1'b0;
                            fault_oob_addr <= 1'b1;
                        end
                    end
                    OP_REFRESH_CFG: begin
                        safe_clamped   <= rx_clamp;
                        refresh_en     <= (~rx_clamp) & rx_tag[0];
                        ref_dwell_cfg  <= (rx_addr == 7'd0) ? 7'd1 : rx_addr;
                        ref_dwell_cnt  <= 7'd0;
                        ref_addr       <= 7'd0;
                        fault_oob_addr <= 1'b0;
                    end
                    OP_ALL_SAFE_ZERO: begin
                        safe_clamped   <= 1'b1;
                        refresh_en     <= 1'b0;
                        cmd_valid_hold <= 1'b0;
                        fault_oob_addr <= 1'b0;
                    end
                    default: begin
                        safe_clamped   <= 1'b1;
                        cmd_valid_hold <= 1'b0;
                    end
                endcase
            end else if (refresh_en && !safe_clamped) begin
                // Cyclic 0..120 S&H refresh scan
                if (ref_dwell_cnt >= (ref_dwell_cfg - 7'd1)) begin
                    ref_dwell_cnt <= 7'd0;
                    if (ref_addr >= MAX_GATE_ADDR)
                        ref_addr <= 7'd0;
                    else
                        ref_addr <= ref_addr + 7'd1;
                end else begin
                    ref_dwell_cnt <= ref_dwell_cnt + 7'd1;
                end
            end

            // Registered strictly 1-hot 11x11 crossbar + 121-gate switch outputs
            if (target_en_c && (target_addr_c <= MAX_GATE_ADDR)) begin
                row_sel          <= (ROW_ONE  << dec_row);
                col_sel          <= (COL_ONE  << dec_col);
                gate_sel         <= (GATE_ONE << target_addr_c);
                active_gate_addr <= target_addr_c;
                gate_valid       <= 1'b1;
            end else begin
                row_sel          <= {N_ROWS{1'b0}};
                col_sel          <= {N_COLS{1'b0}};
                gate_sel         <= {N_GATES{1'b0}};
                active_gate_addr <= 7'd0;
                gate_valid       <= 1'b0;
            end
        end
    end
endmodule
