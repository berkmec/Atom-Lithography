// boed_lut_rom.v - Synthesizable 512-entry Dual-Port BRAM36 Q16.16 LUT + Pipelined Linear Interpolator
// Target: Xilinx Zynq UltraScale+ RFSoC ZU48DR @ 250 MHz (4.0 ns period)
// Exact bit-for-bit hardware realization of fpga_boed_dsp.lut_interp_q16():
//   addr_q8 = (max(x_q16, 0) * SCALE_ADDR) >>> 16
//   idx     = addr_clamped[16:8]  (0..511)
//   frac    = addr_clamped[7:0]   (0..255)
//   y_out   = y0 + (((y1 - y0) * frac + 128) >>> 8)   if in_range else TAIL_WORD
//
// Latency: 4 clock cycles (fully pipelined for high Fmax closure):
//   Stage 0: x_pos * SCALE_ADDR + range clamp -> registered BRAM addresses (breaks mult->BRAM path)
//   Stage 1: Reset-less Dual-Port Synchronous BRAM Read (clean Yosys/Vivado BRAM inference)
//   Stage 2: Signed interpolation multiply (y1 - y0) * frac -> registered product
//   Stage 3: Rounding shift + y0 add + out-of-range tail mux -> registered y_q16
`timescale 1ns/1ps

module boed_lut_rom #(
    parameter        MEM_FILE   = "rom_loglik_p0.hex",
    parameter [31:0] SCALE_ADDR = 32'd10923,
    parameter [31:0] GUARD_WORD = 32'h000001C4,
    parameter [31:0] TAIL_WORD  = 32'h000001C4
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               in_valid,
    input  wire signed [31:0] x_q16,
    output reg                out_valid,
    output reg  signed [31:0] y_q16
);
    localparam [47:0] MAX_ADDR_Q8 = 48'd131071; // (512 << 8) - 1

    (* rom_style = "block" *)
    reg [31:0] rom [0:511];

    // Standard BRAM ROM initialization (synthesizable in Vivado/Quartus/Yosys)
    initial begin
        $readmemh(MEM_FILE, rom);
    end

    // Pipeline Stage 0: Address scaling & range clamp registered BEFORE BRAM read
    wire [31:0] x_pos      = x_q16[31] ? 32'd0 : x_q16;
    wire [63:0] prod_addr  = {32'd0, x_pos} * {32'd0, SCALE_ADDR};
    wire [47:0] addr_q8    = prod_addr[63:16];
    wire        in_range_c = (addr_q8 <= MAX_ADDR_Q8);
    wire [16:0] addr_clmp  = in_range_c ? addr_q8[16:0] : 17'h1FFFF;
    wire [8:0]  idx_a_c    = addr_clmp[16:8];
    wire [8:0]  idx_b_c    = idx_a_c + 9'd1;
    wire [7:0]  frac_c     = addr_clmp[7:0];

    reg        v_s0;
    reg        in_range_s0;
    reg        is_last_s0;
    reg [8:0]  idx_a_s0;
    reg [8:0]  idx_b_s0;
    reg [7:0]  frac_s0;

    always @(posedge clk) begin
        if (!rst_n) begin
            v_s0        <= 1'b0;
            in_range_s0 <= 1'b0;
            is_last_s0  <= 1'b0;
            idx_a_s0    <= 9'd0;
            idx_b_s0    <= 9'd0;
            frac_s0     <= 8'd0;
        end else begin
            v_s0        <= in_valid;
            in_range_s0 <= in_range_c;
            is_last_s0  <= (idx_a_c == 9'd511);
            idx_a_s0    <= idx_a_c;
            idx_b_s0    <= idx_b_c;
            frac_s0     <= frac_c;
        end
    end

    // Pipeline Stage 1A: Reset-less Dual-Port Synchronous BRAM Read (clean Yosys/Vivado BRAM inference)
    reg [31:0] rom_dout_a;
    reg [31:0] rom_dout_b;

    always @(posedge clk) begin
        rom_dout_a <= rom[idx_a_s0];
        rom_dout_b <= rom[idx_b_s0];
    end

    // Pipeline Stage 1B: Control & Guard Metadata
    reg        v_s1;
    reg        in_range_s1;
    reg        is_last_s1;
    reg [7:0]  frac_s1;

    always @(posedge clk) begin
        if (!rst_n) begin
            v_s1        <= 1'b0;
            in_range_s1 <= 1'b0;
            is_last_s1  <= 1'b0;
            frac_s1     <= 8'd0;
        end else begin
            v_s1        <= v_s0;
            in_range_s1 <= in_range_s0;
            is_last_s1  <= is_last_s0;
            frac_s1     <= frac_s0;
        end
    end

    // Pipeline Stage 2: Signed 8-bit linear-interpolation multiply (registered product)
    wire signed [31:0] y0_s1     = $signed(rom_dout_a);
    wire signed [31:0] y1_s1     = is_last_s1 ? $signed(GUARD_WORD) : $signed(rom_dout_b);
    wire signed [32:0] dy_s1     = $signed({y1_s1[31], y1_s1}) - $signed({y0_s1[31], y0_s1});
    wire signed [41:0] dy_ext    = {{9{dy_s1[32]}}, dy_s1};
    wire signed [41:0] frac_ext  = {34'd0, frac_s1};
    wire signed [41:0] frac_prod = dy_ext * frac_ext;

    reg                v_s2;
    reg                in_range_s2;
    reg signed [31:0]  y0_s2;
    reg signed [41:0]  frac_prod_s2;

    always @(posedge clk) begin
        if (!rst_n) begin
            v_s2         <= 1'b0;
            in_range_s2  <= 1'b0;
            y0_s2        <= 32'sd0;
            frac_prod_s2 <= 42'sd0;
        end else begin
            v_s2         <= v_s1;
            in_range_s2  <= in_range_s1;
            y0_s2        <= y0_s1;
            frac_prod_s2 <= frac_prod;
        end
    end

    // Pipeline Stage 3: Final rounding shift + y0 add + tail clamp
    wire signed [41:0] frac_round = frac_prod_s2 + 42'sd128;
    wire signed [31:0] interp_s2  = y0_s2 + $signed(frac_round[39:8]);

    // Explicitly sink unused low-order rounding bits for clean -Wall linting
    wire _unused_ok = &{1'b0, prod_addr[15:0], frac_round[41:40], frac_round[7:0]};

    always @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            y_q16     <= 32'sd0;
        end else begin
            out_valid <= v_s2;
            y_q16     <= in_range_s2 ? interp_s2 : $signed(TAIL_WORD);
        end
    end
endmodule
