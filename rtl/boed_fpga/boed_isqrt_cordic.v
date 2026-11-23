// boed_isqrt_cordic.v - Synthesizable 16-Stage Pipelined Non-Restoring/Restoring Integer Sqrt
// Target: Xilinx Zynq UltraScale+ RFSoC ZU48DR @ 250 MHz (4.0 ns period)
// Computes exact floor(sqrt(radicand[31:0])) -> root[15:0] (0 LSB error vs Python math.isqrt).
// Latency: 16 clock cycles; throughput: 1 result per clock cycle.
`timescale 1ns/1ps

module boed_isqrt_cordic (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    input  wire [31:0] radicand,
    output wire        out_valid,
    output wire [15:0] root
);
    // 16 pipeline stages (k = 0..15) extracting MSB-to-LSB root bits [15..0]
    reg        v_pipe   [0:15];
    reg [31:0] rad_pipe [0:15];
    reg [17:0] rem_pipe [0:15];
    reg [15:0] q_pipe   [0:15];

    // Stage 0 (MSB pair radicand[31:30])
    wire [17:0] rem0_next = {16'd0, radicand[31:30]};
    wire [17:0] sub0_val  = 18'd1;
    wire        ge0       = (rem0_next >= sub0_val);

    always @(posedge clk) begin
        if (!rst_n) begin
            v_pipe[0]   <= 1'b0;
            rad_pipe[0] <= 32'd0;
            rem_pipe[0] <= 18'd0;
            q_pipe[0]   <= 16'd0;
        end else begin
            v_pipe[0]   <= in_valid;
            rad_pipe[0] <= {radicand[29:0], 2'b00};
            rem_pipe[0] <= ge0 ? (rem0_next - sub0_val) : rem0_next;
            q_pipe[0]   <= {15'd0, ge0};
        end
    end

    // Stages 1..15
    genvar s;
    generate
        for (s = 1; s < 16; s = s + 1) begin : gen_isqrt_stage
            wire [17:0] rem_shift = {rem_pipe[s-1][15:0], rad_pipe[s-1][31:30]};
            wire [17:0] trial_sub = {q_pipe[s-1], 2'b01};
            wire        ge_s      = (rem_shift >= trial_sub);

            always @(posedge clk) begin
                if (!rst_n) begin
                    v_pipe[s]   <= 1'b0;
                    rad_pipe[s] <= 32'd0;
                    rem_pipe[s] <= 18'd0;
                    q_pipe[s]   <= 16'd0;
                end else begin
                    v_pipe[s]   <= v_pipe[s-1];
                    rad_pipe[s] <= {rad_pipe[s-1][29:0], 2'b00};
                    rem_pipe[s] <= ge_s ? (rem_shift - trial_sub) : rem_shift;
                    q_pipe[s]   <= {q_pipe[s-1][14:0], ge_s};
                end
            end
        end
    endgenerate

    assign out_valid = v_pipe[15];
    assign root      = q_pipe[15];
endmodule
