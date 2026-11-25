// cryo_mux_ddc_ctrl.v - Parameterizable Multi-Tone Cryo MUX NCO IQ DDC & Qubit Discriminator
// BOM Traceability: S6.6-06, S6.11-01 (Exp140 / programmer.py::execute_mux_readout)
// Target Clock    : 100.0 MHz (10.0 ns period)
//
// Features:
//   - Parameterizable N_CH = 8 default, time-multiplexed up to 32 tones (N_CH = 1..32)
//   - Per-tone 24-bit unsigned NCO phase accumulator & tuning word `phase_inc`
//   - Exact 256-entry midpoint-symmetric Q1.15 quarter-wave sin/cos LUT ROM:
//       qsin_lut[k] = round(32767 * sin((k + 0.5) * (pi/2) / 256))
//     with exact 4-quadrant mirror (zero corner error)
//   - Signed I/Q downconversion mixer:
//       I_mix = round((x * cos(phi)) / 2^15), Q_mix = round((-x * sin(phi)) / 2^15)
//   - Optional matched-filter envelope weighting (`mf_en=1`) or exact boxcar (`mf_en=0`)
//   - Programmable integration window `cfg_win_len` (e.g., 2.0 us readout window)
//   - Per-tone rotated-axis threshold discriminator:
//       proj = round((acc_i * rot_cos + acc_q * rot_sin) / 2^15)
//       qubit_state[c] = (proj >= thresh[c]) ? 1'b1 : 1'b0
//   - Full AXI4-Stream Master output (`m_axis_tvalid/tready/tdata/tid/tlast`) ready to
//     feed `boed_q16_core` (m_axis_tdata[31:0] = signed rotated projection)
//   - ZERO combinational '/' operators, ZERO latches, ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module cryo_mux_ddc_ctrl #(
    parameter integer N_CH = 8 // 1..32 tones (default 8; time-multiplexed up to 32)
) (
    input  wire               clk,
    input  wire               rst_n,

    // Control inputs
    input  wire               enable,
    input  wire               soft_clear,
    input  wire               mf_en,
    input  wire        [4:0]  cfg_num_ch_m1, // active tones - 1 (clamped to N_CH-1)
    input  wire        [15:0] cfg_win_len,   // integration samples per readout window (>= 1)

    // Per-channel configuration CSR write/read ports
    input  wire        [4:0]  cfg_ch_addr,
    input  wire               cfg_phase_we,
    input  wire        [23:0] cfg_phase_inc,
    input  wire               cfg_rot_we,
    input  wire signed [15:0] cfg_rot_cos,
    input  wire signed [15:0] cfg_rot_sin,
    input  wire               cfg_thresh_we,
    input  wire signed [31:0] cfg_thresh,

    // ADC sample + optional matched-filter weight input stream
    input  wire               adc_valid,
    output wire               adc_ready,
    input  wire signed [15:0] adc_sample,
    input  wire signed [15:0] mf_weight,     // Q1.15 signed envelope weight (used when mf_en=1)

    // AXI4-Stream Master Output (ready to feed boed_q16_core)
    output wire               m_axis_tvalid,
    input  wire               m_axis_tready,
    output wire        [63:0] m_axis_tdata,  // [31:0]=proj, [32]=state, [37:33]=ch_id, [63:38]=0
    output wire        [4:0]  m_axis_tid,
    output wire               m_axis_tlast,

    // Readout & telemetry outputs
    output wire               busy,
    output reg                readout_done_pulse,
    output reg                readout_done_sticky,
    output reg  [N_CH-1:0]    qubit_state_mask,
    output reg  [15:0]        sample_cnt_out,
    output reg  [15:0]        window_count,
    output wire signed [31:0] rd_res_i,
    output wire signed [31:0] rd_res_q,
    output wire signed [31:0] rd_res_proj
);
    localparam integer N_CH_M1_INT = N_CH - 1;
    localparam [4:0]   MAX_CH_M1   = N_CH_M1_INT[4:0];
    localparam integer CH_W        = (N_CH <= 2) ? 1 :
                                     (N_CH <= 4) ? 2 :
                                     (N_CH <= 8) ? 3 :
                                     (N_CH <= 16) ? 4 : 5;

    // FSM states
    localparam [2:0] ST_IDLE     = 3'd0;
    localparam [2:0] ST_WEIGHT   = 3'd1;
    localparam [2:0] ST_MIX_LUT  = 3'd2;
    localparam [2:0] ST_MIX_ACC  = 3'd3;
    localparam [2:0] ST_DISC_MUL = 3'd4;
    localparam [2:0] ST_DISC_DEC = 3'd5;
    localparam [2:0] ST_AXIS_TX  = 3'd6;

    // Exact 256-entry Q1.15 midpoint-symmetric quarter-wave sine ROM
    // qsin_lut(k) = round(32767 * sin((k + 0.5) * (pi/2) / 256))
    function [15:0] qsin_lut;
        input [7:0] idx;
        begin
            case (idx)
                8'd  0: qsin_lut = 16'd  101; 8'd  1: qsin_lut = 16'd  302; 8'd  2: qsin_lut = 16'd  503; 8'd  3: qsin_lut = 16'd  704;
                8'd  4: qsin_lut = 16'd  905; 8'd  5: qsin_lut = 16'd 1106; 8'd  6: qsin_lut = 16'd 1307; 8'd  7: qsin_lut = 16'd 1507;
                8'd  8: qsin_lut = 16'd 1708; 8'd  9: qsin_lut = 16'd 1909; 8'd 10: qsin_lut = 16'd 2110; 8'd 11: qsin_lut = 16'd 2310;
                8'd 12: qsin_lut = 16'd 2511; 8'd 13: qsin_lut = 16'd 2711; 8'd 14: qsin_lut = 16'd 2911; 8'd 15: qsin_lut = 16'd 3112;
                8'd 16: qsin_lut = 16'd 3312; 8'd 17: qsin_lut = 16'd 3512; 8'd 18: qsin_lut = 16'd 3712; 8'd 19: qsin_lut = 16'd 3911;
                8'd 20: qsin_lut = 16'd 4111; 8'd 21: qsin_lut = 16'd 4310; 8'd 22: qsin_lut = 16'd 4509; 8'd 23: qsin_lut = 16'd 4708;
                8'd 24: qsin_lut = 16'd 4907; 8'd 25: qsin_lut = 16'd 5106; 8'd 26: qsin_lut = 16'd 5305; 8'd 27: qsin_lut = 16'd 5503;
                8'd 28: qsin_lut = 16'd 5701; 8'd 29: qsin_lut = 16'd 5899; 8'd 30: qsin_lut = 16'd 6096; 8'd 31: qsin_lut = 16'd 6294;
                8'd 32: qsin_lut = 16'd 6491; 8'd 33: qsin_lut = 16'd 6688; 8'd 34: qsin_lut = 16'd 6885; 8'd 35: qsin_lut = 16'd 7081;
                8'd 36: qsin_lut = 16'd 7277; 8'd 37: qsin_lut = 16'd 7473; 8'd 38: qsin_lut = 16'd 7669; 8'd 39: qsin_lut = 16'd 7864;
                8'd 40: qsin_lut = 16'd 8059; 8'd 41: qsin_lut = 16'd 8254; 8'd 42: qsin_lut = 16'd 8448; 8'd 43: qsin_lut = 16'd 8642;
                8'd 44: qsin_lut = 16'd 8836; 8'd 45: qsin_lut = 16'd 9030; 8'd 46: qsin_lut = 16'd 9223; 8'd 47: qsin_lut = 16'd 9416;
                8'd 48: qsin_lut = 16'd 9608; 8'd 49: qsin_lut = 16'd 9800; 8'd 50: qsin_lut = 16'd 9992; 8'd 51: qsin_lut = 16'd10183;
                8'd 52: qsin_lut = 16'd10374; 8'd 53: qsin_lut = 16'd10564; 8'd 54: qsin_lut = 16'd10754; 8'd 55: qsin_lut = 16'd10944;
                8'd 56: qsin_lut = 16'd11133; 8'd 57: qsin_lut = 16'd11322; 8'd 58: qsin_lut = 16'd11511; 8'd 59: qsin_lut = 16'd11699;
                8'd 60: qsin_lut = 16'd11886; 8'd 61: qsin_lut = 16'd12074; 8'd 62: qsin_lut = 16'd12260; 8'd 63: qsin_lut = 16'd12446;
                8'd 64: qsin_lut = 16'd12632; 8'd 65: qsin_lut = 16'd12817; 8'd 66: qsin_lut = 16'd13002; 8'd 67: qsin_lut = 16'd13187;
                8'd 68: qsin_lut = 16'd13370; 8'd 69: qsin_lut = 16'd13554; 8'd 70: qsin_lut = 16'd13736; 8'd 71: qsin_lut = 16'd13919;
                8'd 72: qsin_lut = 16'd14101; 8'd 73: qsin_lut = 16'd14282; 8'd 74: qsin_lut = 16'd14462; 8'd 75: qsin_lut = 16'd14643;
                8'd 76: qsin_lut = 16'd14822; 8'd 77: qsin_lut = 16'd15001; 8'd 78: qsin_lut = 16'd15180; 8'd 79: qsin_lut = 16'd15358;
                8'd 80: qsin_lut = 16'd15535; 8'd 81: qsin_lut = 16'd15712; 8'd 82: qsin_lut = 16'd15888; 8'd 83: qsin_lut = 16'd16063;
                8'd 84: qsin_lut = 16'd16238; 8'd 85: qsin_lut = 16'd16413; 8'd 86: qsin_lut = 16'd16586; 8'd 87: qsin_lut = 16'd16759;
                8'd 88: qsin_lut = 16'd16932; 8'd 89: qsin_lut = 16'd17104; 8'd 90: qsin_lut = 16'd17275; 8'd 91: qsin_lut = 16'd17445;
                8'd 92: qsin_lut = 16'd17615; 8'd 93: qsin_lut = 16'd17784; 8'd 94: qsin_lut = 16'd17953; 8'd 95: qsin_lut = 16'd18121;
                8'd 96: qsin_lut = 16'd18288; 8'd 97: qsin_lut = 16'd18454; 8'd 98: qsin_lut = 16'd18620; 8'd 99: qsin_lut = 16'd18785;
                8'd100: qsin_lut = 16'd18950; 8'd101: qsin_lut = 16'd19113; 8'd102: qsin_lut = 16'd19276; 8'd103: qsin_lut = 16'd19438;
                8'd104: qsin_lut = 16'd19600; 8'd105: qsin_lut = 16'd19761; 8'd106: qsin_lut = 16'd19921; 8'd107: qsin_lut = 16'd20080;
                8'd108: qsin_lut = 16'd20238; 8'd109: qsin_lut = 16'd20396; 8'd110: qsin_lut = 16'd20553; 8'd111: qsin_lut = 16'd20709;
                8'd112: qsin_lut = 16'd20865; 8'd113: qsin_lut = 16'd21019; 8'd114: qsin_lut = 16'd21173; 8'd115: qsin_lut = 16'd21326;
                8'd116: qsin_lut = 16'd21479; 8'd117: qsin_lut = 16'd21630; 8'd118: qsin_lut = 16'd21781; 8'd119: qsin_lut = 16'd21930;
                8'd120: qsin_lut = 16'd22079; 8'd121: qsin_lut = 16'd22227; 8'd122: qsin_lut = 16'd22375; 8'd123: qsin_lut = 16'd22521;
                8'd124: qsin_lut = 16'd22667; 8'd125: qsin_lut = 16'd22812; 8'd126: qsin_lut = 16'd22956; 8'd127: qsin_lut = 16'd23099;
                8'd128: qsin_lut = 16'd23241; 8'd129: qsin_lut = 16'd23382; 8'd130: qsin_lut = 16'd23522; 8'd131: qsin_lut = 16'd23662;
                8'd132: qsin_lut = 16'd23801; 8'd133: qsin_lut = 16'd23938; 8'd134: qsin_lut = 16'd24075; 8'd135: qsin_lut = 16'd24211;
                8'd136: qsin_lut = 16'd24346; 8'd137: qsin_lut = 16'd24480; 8'd138: qsin_lut = 16'd24613; 8'd139: qsin_lut = 16'd24746;
                8'd140: qsin_lut = 16'd24877; 8'd141: qsin_lut = 16'd25007; 8'd142: qsin_lut = 16'd25137; 8'd143: qsin_lut = 16'd25265;
                8'd144: qsin_lut = 16'd25393; 8'd145: qsin_lut = 16'd25519; 8'd146: qsin_lut = 16'd25645; 8'd147: qsin_lut = 16'd25770;
                8'd148: qsin_lut = 16'd25893; 8'd149: qsin_lut = 16'd26016; 8'd150: qsin_lut = 16'd26138; 8'd151: qsin_lut = 16'd26259;
                8'd152: qsin_lut = 16'd26378; 8'd153: qsin_lut = 16'd26497; 8'd154: qsin_lut = 16'd26615; 8'd155: qsin_lut = 16'd26732;
                8'd156: qsin_lut = 16'd26848; 8'd157: qsin_lut = 16'd26962; 8'd158: qsin_lut = 16'd27076; 8'd159: qsin_lut = 16'd27189;
                8'd160: qsin_lut = 16'd27300; 8'd161: qsin_lut = 16'd27411; 8'd162: qsin_lut = 16'd27521; 8'd163: qsin_lut = 16'd27629;
                8'd164: qsin_lut = 16'd27737; 8'd165: qsin_lut = 16'd27843; 8'd166: qsin_lut = 16'd27949; 8'd167: qsin_lut = 16'd28053;
                8'd168: qsin_lut = 16'd28157; 8'd169: qsin_lut = 16'd28259; 8'd170: qsin_lut = 16'd28360; 8'd171: qsin_lut = 16'd28460;
                8'd172: qsin_lut = 16'd28560; 8'd173: qsin_lut = 16'd28658; 8'd174: qsin_lut = 16'd28755; 8'd175: qsin_lut = 16'd28850;
                8'd176: qsin_lut = 16'd28945; 8'd177: qsin_lut = 16'd29039; 8'd178: qsin_lut = 16'd29131; 8'd179: qsin_lut = 16'd29223;
                8'd180: qsin_lut = 16'd29313; 8'd181: qsin_lut = 16'd29403; 8'd182: qsin_lut = 16'd29491; 8'd183: qsin_lut = 16'd29578;
                8'd184: qsin_lut = 16'd29664; 8'd185: qsin_lut = 16'd29749; 8'd186: qsin_lut = 16'd29832; 8'd187: qsin_lut = 16'd29915;
                8'd188: qsin_lut = 16'd29997; 8'd189: qsin_lut = 16'd30077; 8'd190: qsin_lut = 16'd30156; 8'd191: qsin_lut = 16'd30234;
                8'd192: qsin_lut = 16'd30311; 8'd193: qsin_lut = 16'd30387; 8'd194: qsin_lut = 16'd30462; 8'd195: qsin_lut = 16'd30535;
                8'd196: qsin_lut = 16'd30607; 8'd197: qsin_lut = 16'd30679; 8'd198: qsin_lut = 16'd30749; 8'd199: qsin_lut = 16'd30818;
                8'd200: qsin_lut = 16'd30885; 8'd201: qsin_lut = 16'd30952; 8'd202: qsin_lut = 16'd31017; 8'd203: qsin_lut = 16'd31082;
                8'd204: qsin_lut = 16'd31145; 8'd205: qsin_lut = 16'd31206; 8'd206: qsin_lut = 16'd31267; 8'd207: qsin_lut = 16'd31327;
                8'd208: qsin_lut = 16'd31385; 8'd209: qsin_lut = 16'd31442; 8'd210: qsin_lut = 16'd31498; 8'd211: qsin_lut = 16'd31553;
                8'd212: qsin_lut = 16'd31607; 8'd213: qsin_lut = 16'd31659; 8'd214: qsin_lut = 16'd31710; 8'd215: qsin_lut = 16'd31760;
                8'd216: qsin_lut = 16'd31809; 8'd217: qsin_lut = 16'd31857; 8'd218: qsin_lut = 16'd31903; 8'd219: qsin_lut = 16'd31949;
                8'd220: qsin_lut = 16'd31993; 8'd221: qsin_lut = 16'd32036; 8'd222: qsin_lut = 16'd32077; 8'd223: qsin_lut = 16'd32118;
                8'd224: qsin_lut = 16'd32157; 8'd225: qsin_lut = 16'd32195; 8'd226: qsin_lut = 16'd32232; 8'd227: qsin_lut = 16'd32267;
                8'd228: qsin_lut = 16'd32302; 8'd229: qsin_lut = 16'd32335; 8'd230: qsin_lut = 16'd32367; 8'd231: qsin_lut = 16'd32397;
                8'd232: qsin_lut = 16'd32427; 8'd233: qsin_lut = 16'd32455; 8'd234: qsin_lut = 16'd32482; 8'd235: qsin_lut = 16'd32508;
                8'd236: qsin_lut = 16'd32533; 8'd237: qsin_lut = 16'd32556; 8'd238: qsin_lut = 16'd32578; 8'd239: qsin_lut = 16'd32599;
                8'd240: qsin_lut = 16'd32619; 8'd241: qsin_lut = 16'd32637; 8'd242: qsin_lut = 16'd32655; 8'd243: qsin_lut = 16'd32671;
                8'd244: qsin_lut = 16'd32685; 8'd245: qsin_lut = 16'd32699; 8'd246: qsin_lut = 16'd32711; 8'd247: qsin_lut = 16'd32722;
                8'd248: qsin_lut = 16'd32732; 8'd249: qsin_lut = 16'd32741; 8'd250: qsin_lut = 16'd32748; 8'd251: qsin_lut = 16'd32755;
                8'd252: qsin_lut = 16'd32759; 8'd253: qsin_lut = 16'd32763; 8'd254: qsin_lut = 16'd32766; 8'd255: qsin_lut = 16'd32767;
            endcase
        end
    endfunction

    // Per-channel state & configuration arrays
    reg        [23:0] phase_inc [0:N_CH-1];
    reg        [23:0] phase_acc [0:N_CH-1];
    reg signed [15:0] rot_cos   [0:N_CH-1];
    reg signed [15:0] rot_sin   [0:N_CH-1];
    reg signed [31:0] thresh    [0:N_CH-1];
    reg signed [31:0] acc_i     [0:N_CH-1];
    reg signed [31:0] acc_q     [0:N_CH-1];
    reg signed [31:0] res_i     [0:N_CH-1];
    reg signed [31:0] res_q     [0:N_CH-1];
    reg signed [31:0] res_proj  [0:N_CH-1];

    // FSM registers
    reg [2:0]         state;
    reg [4:0]         ch_idx;
    reg [4:0]         ch_last_r;
    reg [15:0]        win_len_r;
    reg signed [15:0] x_adc_r;
    reg signed [15:0] mf_w_r;
    reg               mf_en_r;
    reg signed [15:0] x_weighted_r;
    reg signed [31:0] prod_i_r;
    reg signed [31:0] prod_q_r;
    reg signed [47:0] proj_i_p;
    reg signed [47:0] proj_q_p;

    wire [CH_W-1:0] ch_idx_m = ch_idx[CH_W-1:0];
    wire            cfg_ch_in_range;
    wire [4:0]      eff_ch_last;
    generate
        if (N_CH >= 32) begin : g_full32
            assign cfg_ch_in_range = 1'b1;
            assign eff_ch_last     = cfg_num_ch_m1;
        end else begin : g_sub32
            assign cfg_ch_in_range = (cfg_ch_addr <= MAX_CH_M1);
            assign eff_ch_last     = (cfg_num_ch_m1 > MAX_CH_M1) ? MAX_CH_M1 : cfg_num_ch_m1;
        end
    endgenerate
    wire [CH_W-1:0] cfg_ch_m = cfg_ch_in_range ? cfg_ch_addr[CH_W-1:0] : {CH_W{1'b0}};

    // Matched-filter weight combinational rounding
    wire signed [31:0] mf_prod_c = {{16{x_adc_r[15]}}, x_adc_r} * {{16{mf_w_r[15]}}, mf_w_r};
    wire signed [32:0] mf_rnd_c  = {mf_prod_c[31], mf_prod_c} + 33'sd16384;
    wire signed [17:0] mf_q15_c  = $signed(mf_rnd_c[32:15]);
    wire signed [15:0] mf_val_c  = (mf_q15_c > 18'sd32767)  ? 16'sd32767 :
                                   ((mf_q15_c < -18'sd32768) ? -16'sd32768 : mf_q15_c[15:0]);

    // NCO quadrant decode & quarter-wave LUT lookup for current ch_idx
    wire [23:0] cur_phi     = phase_acc[ch_idx_m];
    wire [1:0]  phi_quad    = cur_phi[23:22];
    wire [7:0]  phi_qidx    = cur_phi[21:14];
    wire [7:0]  phi_qidx_m  = 8'd255 - phi_qidx;
    wire [15:0] lut_sin_mag = qsin_lut(phi_qidx);
    wire [15:0] lut_cos_mag = qsin_lut(phi_qidx_m);

    reg signed [16:0] nco_sin_c;
    reg signed [16:0] nco_cos_c;
    always @(*) begin
        case (phi_quad)
            2'b00: begin
                nco_sin_c =  $signed({1'b0, lut_sin_mag});
                nco_cos_c =  $signed({1'b0, lut_cos_mag});
            end
            2'b01: begin
                nco_sin_c =  $signed({1'b0, lut_cos_mag});
                nco_cos_c = -$signed({1'b0, lut_sin_mag});
            end
            2'b10: begin
                nco_sin_c = -$signed({1'b0, lut_sin_mag});
                nco_cos_c = -$signed({1'b0, lut_cos_mag});
            end
            default: begin
                nco_sin_c = -$signed({1'b0, lut_cos_mag});
                nco_cos_c =  $signed({1'b0, lut_sin_mag});
            end
        endcase
    end

    wire signed [31:0] x_ext32   = {{16{x_weighted_r[15]}}, x_weighted_r};
    wire signed [31:0] cos_ext32 = {{15{nco_cos_c[16]}}, nco_cos_c};
    wire signed [31:0] sin_ext32 = {{15{nco_sin_c[16]}}, nco_sin_c};
    wire signed [31:0] mix_p_i   = x_ext32 * cos_ext32;
    wire signed [31:0] mix_p_q   = -(x_ext32 * sin_ext32);

    // Exact Q1.15 rounded mixer outputs
    wire signed [32:0] pi_rnd33  = {prod_i_r[31], prod_i_r} + 33'sd16384;
    wire signed [32:0] pq_rnd33  = {prod_q_r[31], prod_q_r} + 33'sd16384;
    wire signed [31:0] mix_i_q   = {{14{pi_rnd33[32]}}, pi_rnd33[32:15]};
    wire signed [31:0] mix_q_q   = {{14{pq_rnd33[32]}}, pq_rnd33[32:15]};

    // Exact Q1.15 rotated-axis projection
    wire signed [47:0] proj_sum48 = proj_i_p + proj_q_p + 48'sd16384;
    wire signed [31:0] proj_val32 = $signed(proj_sum48[46:15]);
    wire               disc_bit_c = (proj_val32 >= thresh[ch_idx_m]);

    // Outputs
    assign adc_ready     = enable && (state == ST_IDLE);
    assign busy          = (state != ST_IDLE);
    assign m_axis_tvalid = (state == ST_AXIS_TX);
    assign m_axis_tid    = ch_idx;
    assign m_axis_tlast  = (ch_idx == ch_last_r);
    assign m_axis_tdata  = {26'd0, ch_idx, qubit_state_mask[ch_idx_m], res_proj[ch_idx_m]};

    assign rd_res_i      = res_i[cfg_ch_m];
    assign rd_res_q      = res_q[cfg_ch_m];
    assign rd_res_proj   = res_proj[cfg_ch_m];

    wire [15:0] eff_win_len = (cfg_win_len == 16'd0) ? 16'd1 : cfg_win_len;

    // Sink unused low-order rounding & phase bits cleanly for Verilator -Wall
    wire _unused_ok = &{1'b0, cur_phi[13:0], mf_rnd_c[14:0], pi_rnd33[14:0], pq_rnd33[14:0],
                        proj_sum48[47], proj_sum48[14:0]};

    integer k;

    always @(posedge clk) begin
        if (!rst_n) begin
            state               <= ST_IDLE;
            ch_idx              <= 5'd0;
            ch_last_r           <= MAX_CH_M1;
            win_len_r           <= 16'd1;
            x_adc_r             <= 16'sd0;
            mf_w_r              <= 16'sd32767;
            mf_en_r             <= 1'b0;
            x_weighted_r        <= 16'sd0;
            prod_i_r            <= 32'sd0;
            prod_q_r            <= 32'sd0;
            proj_i_p            <= 48'sd0;
            proj_q_p            <= 48'sd0;
            readout_done_pulse  <= 1'b0;
            readout_done_sticky <= 1'b0;
            qubit_state_mask    <= {N_CH{1'b0}};
            sample_cnt_out      <= 16'd0;
            window_count        <= 16'd0;
            for (k = 0; k < N_CH; k = k + 1) begin
                phase_inc[k] <= 24'd0;
                phase_acc[k] <= 24'd0;
                rot_cos[k]   <= 16'sd32767;
                rot_sin[k]   <= 16'sd0;
                thresh[k]    <= 32'sd0;
                acc_i[k]     <= 32'sd0;
                acc_q[k]     <= 32'sd0;
                res_i[k]     <= 32'sd0;
                res_q[k]     <= 32'sd0;
                res_proj[k]  <= 32'sd0;
            end
        end else begin
            readout_done_pulse <= 1'b0;

            // Per-channel CSR configuration writes
            if (cfg_ch_in_range) begin
                if (cfg_phase_we) begin
                    phase_inc[cfg_ch_m] <= cfg_phase_inc;
                end
                if (cfg_rot_we) begin
                    rot_cos[cfg_ch_m] <= cfg_rot_cos;
                    rot_sin[cfg_ch_m] <= cfg_rot_sin;
                end
                if (cfg_thresh_we) begin
                    thresh[cfg_ch_m] <= cfg_thresh;
                end
            end

            if (soft_clear) begin
                state               <= ST_IDLE;
                ch_idx              <= 5'd0;
                sample_cnt_out      <= 16'd0;
                readout_done_sticky <= 1'b0;
                qubit_state_mask    <= {N_CH{1'b0}};
                for (k = 0; k < N_CH; k = k + 1) begin
                    phase_acc[k] <= 24'd0;
                    acc_i[k]     <= 32'sd0;
                    acc_q[k]     <= 32'sd0;
                    res_i[k]     <= 32'sd0;
                    res_q[k]     <= 32'sd0;
                    res_proj[k]  <= 32'sd0;
                end
            end else begin
                case (state)
                    ST_IDLE: begin
                        if (enable && adc_valid) begin
                            x_adc_r   <= adc_sample;
                            mf_w_r    <= mf_weight;
                            mf_en_r   <= mf_en;
                            ch_last_r <= eff_ch_last;
                            win_len_r <= eff_win_len;
                            state     <= ST_WEIGHT;
                        end
                    end

                    ST_WEIGHT: begin
                        x_weighted_r <= mf_en_r ? mf_val_c : x_adc_r;
                        ch_idx       <= 5'd0;
                        state        <= ST_MIX_LUT;
                    end

                    ST_MIX_LUT: begin
                        prod_i_r            <= mix_p_i;
                        prod_q_r            <= mix_p_q;
                        phase_acc[ch_idx_m] <= cur_phi + phase_inc[ch_idx_m];
                        state               <= ST_MIX_ACC;
                    end

                    ST_MIX_ACC: begin
                        acc_i[ch_idx_m] <= acc_i[ch_idx_m] + mix_i_q;
                        acc_q[ch_idx_m] <= acc_q[ch_idx_m] + mix_q_q;
                        if (ch_idx == ch_last_r) begin
                            if (sample_cnt_out >= (win_len_r - 16'd1)) begin
                                sample_cnt_out <= 16'd0;
                                ch_idx         <= 5'd0;
                                state          <= ST_DISC_MUL;
                            end else begin
                                sample_cnt_out <= sample_cnt_out + 16'd1;
                                state          <= ST_IDLE;
                            end
                        end else begin
                            ch_idx <= ch_idx + 5'd1;
                            state  <= ST_MIX_LUT;
                        end
                    end

                    ST_DISC_MUL: begin
                        proj_i_p <= {{16{acc_i[ch_idx_m][31]}}, acc_i[ch_idx_m]} *
                                    {{32{rot_cos[ch_idx_m][15]}}, rot_cos[ch_idx_m]};
                        proj_q_p <= {{16{acc_q[ch_idx_m][31]}}, acc_q[ch_idx_m]} *
                                    {{32{rot_sin[ch_idx_m][15]}}, rot_sin[ch_idx_m]};
                        state    <= ST_DISC_DEC;
                    end

                    ST_DISC_DEC: begin
                        res_i[ch_idx_m]            <= acc_i[ch_idx_m];
                        res_q[ch_idx_m]            <= acc_q[ch_idx_m];
                        res_proj[ch_idx_m]         <= proj_val32;
                        qubit_state_mask[ch_idx_m] <= disc_bit_c;
                        acc_i[ch_idx_m]            <= 32'sd0;
                        acc_q[ch_idx_m]            <= 32'sd0;
                        if (ch_idx == ch_last_r) begin
                            window_count        <= window_count + 16'd1;
                            readout_done_pulse  <= 1'b1;
                            readout_done_sticky <= 1'b1;
                            ch_idx              <= 5'd0;
                            state               <= ST_AXIS_TX;
                        end else begin
                            ch_idx <= ch_idx + 5'd1;
                            state  <= ST_DISC_MUL;
                        end
                    end

                    ST_AXIS_TX: begin
                        if (m_axis_tready) begin
                            if (ch_idx == ch_last_r) begin
                                ch_idx <= 5'd0;
                                state  <= ST_IDLE;
                            end else begin
                                ch_idx <= ch_idx + 5'd1;
                            end
                        end
                    end

                    default: begin
                        state <= ST_IDLE;
                    end
                endcase
            end
        end
    end
endmodule
