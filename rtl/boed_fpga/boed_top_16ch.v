// boed_top_16ch.v - 16-Channel Parallel Q16.16 BOED-FPGA Accelerator with AXI4-Stream Wrapper
// Target: Xilinx Zynq UltraScale+ RFSoC ZU48DR @ 250 MHz (448 DSP48E2 = 10.49%, 64 BRAM36 = 5.93%)
// AXI4-Stream Input Packet (128-bit s_axis_tdata, s_axis_tid[3:0] selects channel 0..15):
//   [31:0]   f_probe_hz     (signed 32-bit Hz)
//   [63:32]  y_meas_q16     (signed Q16.16 measurement sample)
//   [95:64]  f_init_hz      (signed 32-bit prior center Hz)
//   [103:96] step_idx       (8-bit BOED step index)
//   [127:104] reserved/flags ([104]=sprt_mode, [105]=sprt_reset_llr)
// AXI4-Stream Output Packet (96-bit m_axis_tdata, m_axis_tid[3:0] = completing channel):
//   [31:0]   mu_off_q8         (signed Q24.8 Hz offset from f_init_hz)
//   [47:32]  std_q4            (unsigned Q12.4 Hz posterior std)
//   [79:48]  next_probe_off_q8 (signed Q24.8 Hz next Fisher-optimal probe offset)
//   [95:80]  cycle_count       (exact 16-bit hardware cycle count = 16'd584)
`timescale 1ns/1ps

module boed_top_16ch #(
    parameter integer N_CHANNELS   = 16,
    parameter         LOR_HEX_FILE = "rom_loglik_p0.hex",
    parameter         EXP_HEX_FILE = "rom_loglik_p1.hex"
) (
    input  wire                clk,
    input  wire                rst_n,

    // Shared calibration registers (broadcast to all 16 BOED engines)
    input  wire        [31:0]  cfg_inv_gamma_q24,
    input  wire signed [31:0]  cfg_inv_2var_q16,
    input  wire        [15:0]  cfg_delta_fisher_q4,
    input  wire        [15:0]  cfg_max_off_q4,
    input  wire signed [31:0]  cfg_sprt_half_sig_q16,
    input  wire signed [31:0]  cfg_sprt_scale_q16,
    input  wire signed [31:0]  cfg_sprt_thresh_q16,

    // Prior BRAM initialization port (shared across selected channel)
    input  wire                prior_load_en,
    input  wire        [3:0]   prior_load_ch,
    input  wire        [9:0]   prior_load_addr,
    input  wire signed [31:0]  prior_load_lp_q16,

    // AXI4-Stream Slave Input
    input  wire                s_axis_tvalid,
    output wire                s_axis_tready,
    input  wire        [127:0] s_axis_tdata,
    input  wire        [3:0]   s_axis_tid,
    input  wire                s_axis_tlast,

    // AXI4-Stream Master Output
    output reg                 m_axis_tvalid,
    input  wire                m_axis_tready,
    output reg         [95:0]  m_axis_tdata,
    output reg         [3:0]   m_axis_tid,
    output reg                 m_axis_tlast,

    // Telemetry status
    output wire        [15:0]  ch_busy_mask,
    output wire        [15:0]  ch_sprt_donor_mask
);
    wire        [15:0] ch_step_done;
    wire        [15:0] ch_sprt_done;
    wire        [15:0] ch_sprt_dec_valid;
    wire signed [31:0] ch_sprt_llr       [0:15];
    wire signed [31:0] ch_mu_off_q8      [0:15];
    wire        [15:0] ch_std_q4         [0:15];
    wire signed [31:0] ch_next_probe_q8  [0:15];
    wire        [15:0] ch_cycle_count    [0:15];

    // Channel ready if targeted channel is idle
    assign s_axis_tready = ~ch_busy_mask[s_axis_tid];

    // Unpack AXI4-Stream input beat
    wire signed [31:0] in_f_probe_hz   = s_axis_tdata[31:0];
    wire signed [31:0] in_y_meas_q16   = s_axis_tdata[63:32];
    wire signed [31:0] in_f_init_hz    = s_axis_tdata[95:64];
    wire        [7:0]  in_step_idx     = s_axis_tdata[103:96];
    wire               in_sprt_mode    = s_axis_tdata[104];
    wire               in_sprt_reset   = s_axis_tdata[105];
    wire               in_handshake    = s_axis_tvalid && s_axis_tready;

    // 16 parallel boed_q16_core instances (64 total SIMD lanes on ZU48DR)
    genvar ch;
    generate
        for (ch = 0; ch < N_CHANNELS; ch = ch + 1) begin : gen_boed_ch
            wire ch_sel        = (s_axis_tid == ch[3:0]);
            wire ch_step_start = in_handshake && ch_sel && (~in_sprt_mode);
            wire ch_sprt_start = in_handshake && ch_sel && in_sprt_mode;
            wire ch_prior_en   = prior_load_en && (prior_load_ch == ch[3:0]);

            boed_q16_core #(
                .LOR_HEX_FILE(LOR_HEX_FILE),
                .EXP_HEX_FILE(EXP_HEX_FILE)
            ) u_core (
                .clk                (clk),
                .rst_n              (rst_n),
                .sprt_start         (ch_sprt_start),
                .sprt_reset_llr     (ch_sprt_start && in_sprt_reset),
                .sprt_y_q16         (in_y_meas_q16),
                .sprt_half_sig_q16  (cfg_sprt_half_sig_q16),
                .sprt_scale_q16     (cfg_sprt_scale_q16),
                .sprt_thresh_q16    (cfg_sprt_thresh_q16),
                .sprt_done          (ch_sprt_done[ch]),
                .sprt_decision_valid(ch_sprt_dec_valid[ch]),
                .sprt_donor_present (ch_sprt_donor_mask[ch]),
                .sprt_llr_q16       (ch_sprt_llr[ch]),
                .step_start         (ch_step_start),
                .prior_load_en      (ch_prior_en),
                .prior_load_addr    (prior_load_addr),
                .prior_load_lp_q16  (prior_load_lp_q16),
                .f_init_hz          (in_f_init_hz),
                .f_probe_hz         (in_f_probe_hz),
                .y_meas_q16         (in_y_meas_q16),
                .inv_gamma_q24      (cfg_inv_gamma_q24),
                .inv_2var_q16       (cfg_inv_2var_q16),
                .delta_fisher_q4    (cfg_delta_fisher_q4),
                .max_off_q4         (cfg_max_off_q4),
                .step_idx           (in_step_idx),
                .busy               (ch_busy_mask[ch]),
                .step_done          (ch_step_done[ch]),
                .mu_off_q8          (ch_mu_off_q8[ch]),
                .std_q4             (ch_std_q4[ch]),
                .next_probe_off_q8  (ch_next_probe_q8[ch]),
                .cycle_count        (ch_cycle_count[ch])
            );
        end
    endgenerate

    // Pending output completion latches + deterministic priority arbiter for AXI4-Stream TX
    reg [15:0] pending_out;
    reg [3:0]  grant_idx;
    reg        grant_valid;
    integer    k;

    always @(*) begin
        grant_valid = 1'b0;
        grant_idx   = 4'd0;
        for (k = 15; k >= 0; k = k - 1) begin
            if (pending_out[k]) begin
                grant_valid = 1'b1;
                grant_idx   = k[3:0];
            end
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            pending_out   <= 16'd0;
            m_axis_tvalid <= 1'b0;
            m_axis_tdata  <= 96'd0;
            m_axis_tid    <= 4'd0;
            m_axis_tlast  <= 1'b0;
        end else begin
            // Latch any newly completed channels
            pending_out <= pending_out | ch_step_done;

            if (m_axis_tvalid && m_axis_tready) begin
                m_axis_tvalid <= 1'b0;
                m_axis_tlast  <= 1'b0;
            end

            if ((!m_axis_tvalid || m_axis_tready) && grant_valid) begin
                m_axis_tvalid <= 1'b1;
                m_axis_tid    <= grant_idx;
                m_axis_tlast  <= 1'b1;
                m_axis_tdata  <= {
                    ch_cycle_count[grant_idx],
                    ch_next_probe_q8[grant_idx],
                    ch_std_q4[grant_idx],
                    ch_mu_off_q8[grant_idx]
                };
                pending_out[grant_idx] <= ch_step_done[grant_idx];
            end
        end
    end
endmodule
