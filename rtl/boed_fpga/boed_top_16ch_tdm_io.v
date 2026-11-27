// boed_top_16ch_tdm_io.v - Pin-Constrained Serialized/TDM Carrier Wrapper for boed_top_16ch
// Resolves OBS-050 package pin overflow: boed_top_16ch is an internal ZU48DR RFSoC PS-PL
// AXI4-Stream IP core (511 internal bus wires). This wrapper encapsulates all wide calibration,
// prior-BRAM load, and 128b/96b AXI4-Stream buses behind a compact 32-bit TDM physical I/O
// bus totaling 48 physical pins (strictly <= 80-pin XC7K325T carrier & <= 205-pin ECP5-CABGA381).
//
// Physical Pin Count: 1+1 + 1+3+32 + 1+1+1+3+32 + 1+1 + 1+1 = 48+32 -> wait: let's keep it
// 16-bit TDM TX/RX bidirectional-split = 1+1 + 1+1+4+16 (in=22) + 1+1+4+16 (out=22) + 2 (status) = 48 pins!
//
// TDM Input Command Protocol (16-bit `tdm_in_data`, `tdm_in_cmd[3:0]`, `tdm_in_valid`, `tdm_in_ready`):
//   4'h0: Load cfg_inv_gamma_q24     [15:0] (lo)  | 4'h1: [31:16] (hi)
//   4'h2: Load cfg_inv_2var_q16      [15:0] (lo)  | 4'h3: [31:16] (hi)
//   4'h4: Load cfg_delta_fisher_q4   [15:0]       | 4'h5: cfg_max_off_q4 [15:0]
//   4'h6: Load sprt_half/scale/thr   via sub-index (auto-incrementing 6x16b shadow bank)
//   4'h7: Load prior addr+ch         {ch[3:0], 2'b00, addr[9:0]}
//   4'h8: Load prior data lo         [15:0]       | 4'h9: prior data hi [31:16] & pulse prior_load_en
//   4'hA: Load s_axis_tdata word 0..7 (auto-incrementing 8x16b input beat buffer)
//   4'hB: Launch s_axis beat         {11'b0, tlast, tid[3:0]}
//
// TDM Output Telemetry Protocol (16-bit `tdm_out_data`, `tdm_out_word[2:0]`, `tdm_out_valid`, `tdm_out_ready`):
//   Streams each completed 96-bit m_axis_tdata + 4-bit tid as 7 x 16-bit beats:
//     word 0..5 = m_axis_tdata[16*w +: 16], word 6 = {11'd0, m_axis_tlast, m_axis_tid[3:0]}.
`timescale 1ns/1ps

module boed_top_16ch_tdm_io #(
    parameter integer N_CHANNELS   = 16,
    parameter         LOR_HEX_FILE = "rom_loglik_p0.hex",
    parameter         EXP_HEX_FILE = "rom_loglik_p1.hex"
) (
    input  wire        clk,
    input  wire        rst_n,

    // Compact 16-bit TDM Input Channel (22 pins)
    input  wire        tdm_in_valid,
    output wire        tdm_in_ready,
    input  wire [3:0]  tdm_in_cmd,
    input  wire [15:0] tdm_in_data,

    // Compact 16-bit TDM Output Channel (22 pins)
    output wire        tdm_out_valid,
    input  wire        tdm_out_ready,
    output wire [2:0]  tdm_out_word,
    output wire        tdm_out_last,
    output wire [15:0] tdm_out_data,

    // Aggregated Status Pins (2 pins) -> Total physical pins = 48 (<= 80 carrier / <= 205 ECP5)
    output wire        any_ch_busy,
    output wire        any_sprt_donor
);
    // 2-FF async-assert / sync-deassert reset synchronizer
    (* ASYNC_REG = "TRUE" *) reg rst_s1;
    (* ASYNC_REG = "TRUE" *) reg rst_s2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst_s1 <= 1'b0;
            rst_s2 <= 1'b0;
        end else begin
            rst_s1 <= 1'b1;
            rst_s2 <= rst_s1;
        end
    end
    wire rst_sync_n = rst_s2;

    // Shadow registers feeding boed_top_16ch
    reg        [31:0]  r_inv_gamma;
    reg signed [31:0]  r_inv_2var;
    reg        [15:0]  r_delta_fisher;
    reg        [15:0]  r_max_off;
    reg signed [31:0]  r_sprt_half;
    reg signed [31:0]  r_sprt_scale;
    reg signed [31:0]  r_sprt_thresh;
    reg        [2:0]   r_sprt_subidx;

    reg                r_prior_en;
    reg        [3:0]   r_prior_ch;
    reg        [9:0]   r_prior_addr;
    reg signed [31:0]  r_prior_lp;

    reg        [127:0] r_s_tdata;
    reg        [2:0]   r_s_widx;
    reg                r_s_tvalid;
    reg        [3:0]   r_s_tid;
    reg                r_s_tlast;
    wire               w_s_tready;

    wire               w_m_tvalid;
    wire               w_m_tready;
    wire       [95:0]  w_m_tdata;
    wire       [3:0]   w_m_tid;
    wire               w_m_tlast;
    wire       [15:0]  w_ch_busy_mask;
    wire       [15:0]  w_ch_sprt_donor_mask;

    assign any_ch_busy    = |w_ch_busy_mask;
    assign any_sprt_donor = |w_ch_sprt_donor_mask;
    assign tdm_in_ready   = ~r_s_tvalid;

    boed_top_16ch #(
        .N_CHANNELS  (N_CHANNELS),
        .LOR_HEX_FILE(LOR_HEX_FILE),
        .EXP_HEX_FILE(EXP_HEX_FILE)
    ) u_boed_16ch (
        .clk                   (clk),
        .rst_n                 (rst_n),
        .cfg_inv_gamma_q24     (r_inv_gamma),
        .cfg_inv_2var_q16      (r_inv_2var),
        .cfg_delta_fisher_q4   (r_delta_fisher),
        .cfg_max_off_q4        (r_max_off),
        .cfg_sprt_half_sig_q16 (r_sprt_half),
        .cfg_sprt_scale_q16    (r_sprt_scale),
        .cfg_sprt_thresh_q16   (r_sprt_thresh),
        .prior_load_en         (r_prior_en),
        .prior_load_ch         (r_prior_ch),
        .prior_load_addr       (r_prior_addr),
        .prior_load_lp_q16     (r_prior_lp),
        .s_axis_tvalid         (r_s_tvalid),
        .s_axis_tready         (w_s_tready),
        .s_axis_tdata          (r_s_tdata),
        .s_axis_tid            (r_s_tid),
        .s_axis_tlast          (r_s_tlast),
        .m_axis_tvalid         (w_m_tvalid),
        .m_axis_tready         (w_m_tready),
        .m_axis_tdata          (w_m_tdata),
        .m_axis_tid            (w_m_tid),
        .m_axis_tlast          (w_m_tlast),
        .ch_busy_mask          (w_ch_busy_mask),
        .ch_sprt_donor_mask    (w_ch_sprt_donor_mask)
    );

    // Output 7-beat 16-bit TDM serializer
    reg        tx_active;
    reg [2:0]  tx_widx;
    reg [95:0] tx_data_q;
    reg [3:0]  tx_tid_q;
    reg        tx_tlast_q;

    assign w_m_tready    = ~tx_active;
    assign tdm_out_valid = tx_active;
    assign tdm_out_word  = tx_widx;
    assign tdm_out_last  = tx_active && (tx_widx == 3'd6);

    reg [15:0] tx_word_mux;
    always @(*) begin
        case (tx_widx)
            3'd0: tx_word_mux = tx_data_q[15:0];
            3'd1: tx_word_mux = tx_data_q[31:16];
            3'd2: tx_word_mux = tx_data_q[47:32];
            3'd3: tx_word_mux = tx_data_q[63:48];
            3'd4: tx_word_mux = tx_data_q[79:64];
            3'd5: tx_word_mux = tx_data_q[95:80];
            default: tx_word_mux = {11'd0, tx_tlast_q, tx_tid_q};
        endcase
    end
    assign tdm_out_data = tx_word_mux;

    always @(posedge clk) begin
        if (!rst_sync_n) begin
            r_inv_gamma    <= 32'd0;
            r_inv_2var     <= 32'sd0;
            r_delta_fisher <= 16'd0;
            r_max_off      <= 16'd0;
            r_sprt_half    <= 32'sd0;
            r_sprt_scale   <= 32'sd0;
            r_sprt_thresh  <= 32'sd0;
            r_sprt_subidx  <= 3'd0;
            r_prior_en     <= 1'b0;
            r_prior_ch     <= 4'd0;
            r_prior_addr   <= 10'd0;
            r_prior_lp     <= 32'sd0;
            r_s_tdata      <= 128'd0;
            r_s_widx       <= 3'd0;
            r_s_tvalid     <= 1'b0;
            r_s_tid        <= 4'd0;
            r_s_tlast      <= 1'b0;
            tx_active      <= 1'b0;
            tx_widx        <= 3'd0;
            tx_data_q      <= 96'd0;
            tx_tid_q       <= 4'd0;
            tx_tlast_q     <= 1'b0;
        end else begin
            r_prior_en <= 1'b0;
            if (r_s_tvalid && w_s_tready) begin
                r_s_tvalid <= 1'b0;
            end

            if (tdm_in_valid && tdm_in_ready) begin
                case (tdm_in_cmd)
                    4'h0: r_inv_gamma[15:0]  <= tdm_in_data;
                    4'h1: r_inv_gamma[31:16] <= tdm_in_data;
                    4'h2: r_inv_2var[15:0]   <= tdm_in_data;
                    4'h3: r_inv_2var[31:16]  <= tdm_in_data;
                    4'h4: r_delta_fisher     <= tdm_in_data;
                    4'h5: r_max_off          <= tdm_in_data;
                    4'h6: begin
                        case (r_sprt_subidx)
                            3'd0: r_sprt_half[15:0]    <= tdm_in_data;
                            3'd1: r_sprt_half[31:16]   <= tdm_in_data;
                            3'd2: r_sprt_scale[15:0]   <= tdm_in_data;
                            3'd3: r_sprt_scale[31:16]  <= tdm_in_data;
                            3'd4: r_sprt_thresh[15:0]  <= tdm_in_data;
                            default: r_sprt_thresh[31:16] <= tdm_in_data;
                        endcase
                        r_sprt_subidx <= (r_sprt_subidx == 3'd5) ? 3'd0 : (r_sprt_subidx + 3'd1);
                    end
                    4'h7: begin
                        r_prior_ch   <= tdm_in_data[15:12];
                        r_prior_addr <= tdm_in_data[9:0];
                    end
                    4'h8: r_prior_lp[15:0]   <= tdm_in_data;
                    4'h9: begin
                        r_prior_lp[31:16] <= tdm_in_data;
                        r_prior_en        <= 1'b1;
                    end
                    4'hA: begin
                        case (r_s_widx)
                            3'd0: r_s_tdata[15:0]    <= tdm_in_data;
                            3'd1: r_s_tdata[31:16]   <= tdm_in_data;
                            3'd2: r_s_tdata[47:32]   <= tdm_in_data;
                            3'd3: r_s_tdata[63:48]   <= tdm_in_data;
                            3'd4: r_s_tdata[79:64]   <= tdm_in_data;
                            3'd5: r_s_tdata[95:80]   <= tdm_in_data;
                            3'd6: r_s_tdata[111:96]  <= tdm_in_data;
                            default: r_s_tdata[127:112] <= tdm_in_data;
                        endcase
                        r_s_widx <= r_s_widx + 3'd1;
                    end
                    4'hB: begin
                        r_s_tid    <= tdm_in_data[3:0];
                        r_s_tlast  <= tdm_in_data[4];
                        r_s_tvalid <= 1'b1;
                        r_s_widx   <= 3'd0;
                    end
                    default: begin
                        // Ignored
                    end
                endcase
            end

            // Output TDM serializer FSM
            if (!tx_active) begin
                if (w_m_tvalid && w_m_tready) begin
                    tx_active  <= 1'b1;
                    tx_widx    <= 3'd0;
                    tx_data_q  <= w_m_tdata;
                    tx_tid_q   <= w_m_tid;
                    tx_tlast_q <= w_m_tlast;
                end
            end else if (tdm_out_ready) begin
                if (tx_widx == 3'd6) begin
                    tx_active <= 1'b0;
                    tx_widx   <= 3'd0;
                end else begin
                    tx_widx <= tx_widx + 3'd1;
                end
            end
        end
    end
endmodule
