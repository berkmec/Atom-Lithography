// boed_lut_rom.v - Synthesizable 512-entry Dual-Port BRAM36 Q16.16 LUT + Linear Interpolator
// Target: Xilinx Zynq UltraScale+ RFSoC ZU48DR @ 250 MHz (4.0 ns period)
// Exact bit-for-bit hardware realization of fpga_boed_dsp.lut_interp_q16():
//   addr_q8 = (max(x_q16, 0) * SCALE_ADDR) >>> 16
//   idx     = addr_clamped[16:8]  (0..511)
//   frac    = addr_clamped[7:0]   (0..255)
//   y_out   = y0 + (((y1 - y0) * frac + 128) >>> 8)   if in_range else TAIL_WORD
// Latency: 2 clock cycles (Stage 1: BRAM dual-port read; Stage 2: DSP48E2 linear interpolation).
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

    // Combinational address scaling (unsigned clamp x_q16 >= 0)
    wire [31:0] x_pos      = x_q16[31] ? 32'd0 : x_q16;
    wire [63:0] prod_addr  = {32'd0, x_pos} * {32'd0, SCALE_ADDR};
    wire [47:0] addr_q8    = prod_addr[63:16];
    wire        in_range_c = (addr_q8 <= MAX_ADDR_Q8);
    wire [16:0] addr_clmp  = in_range_c ? addr_q8[16:0] : 17'h1FFFF;
    wire [8:0]  idx_a      = addr_clmp[16:8];
    wire [8:0]  idx_b      = idx_a + 9'd1;
    wire [7:0]  frac_c     = addr_clmp[7:0];

    // Pipeline Stage 1: Dual-port BRAM read
    reg               v_s1;
    reg               in_range_s1;
    reg        [7:0]  frac_s1;
    reg signed [31:0] y0_s1;
    reg signed [31:0] y1_s1;

    always @(posedge clk) begin
        if (!rst_n) begin
            v_s1        <= 1'b0;
            in_range_s1 <= 1'b0;
            frac_s1     <= 8'd0;
            y0_s1       <= 32'sd0;
            y1_s1       <= 32'sd0;
        end else begin
            v_s1        <= in_valid;
            in_range_s1 <= in_range_c;
            frac_s1     <= frac_c;
            y0_s1       <= rom[idx_a];
            y1_s1       <= (idx_a == 9'd511) ? GUARD_WORD : rom[idx_b];
        end
    end

    // Pipeline Stage 2: Signed 8-bit rounded linear interpolation
    wire signed [32:0] dy_s1      = $signed({y1_s1[31], y1_s1}) - $signed({y0_s1[31], y0_s1});
    wire signed [41:0] frac_prod  = dy_s1 * $signed({1'b0, frac_s1});
    wire signed [41:0] frac_round = frac_prod + 42'sd128;
    wire signed [31:0] interp_s1  = y0_s1 + frac_round[39:8];

    always @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            y_q16     <= 32'sd0;
        end else begin
            out_valid <= v_s1;
            y_q16     <= in_range_s1 ? interp_s1 : $signed(TAIL_WORD);
        end
    end
endmodule
