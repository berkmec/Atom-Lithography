// uart_axi_regmap.v - Synthesizable UART 8N1 to AXI4-Lite Master CSR Bridge
// BOM Traceability: S3.3-01, S3.3-04, S7.2-02, S8.4-02
// Target Clock    : 100.0 MHz (10.0 ns period), default 115,200 baud (baud_div = 868)
//
// Binary Framed UART Protocol (8N1, LSB-first UART bytes, Big-Endian 16b addr / 32b data):
//   WRITE Command (7 bytes RX -> 1 byte TX ACK):
//     RX: [0x57 'W'] [addr_hi] [addr_lo] [wdata3] [wdata2] [wdata1] [wdata0]
//     TX: [0x4B 'K'] if AXI bresp==2'b00 else [0x45 'E']
//   READ Command  (3 bytes RX -> 5 bytes TX RESP):
//     RX: [0x52 'R'] [addr_hi] [addr_lo]
//     TX: [0x44 'D'] [rdata3] [rdata2] [rdata1] [rdata0]
//   Unknown command opcode bytes are ignored safely without wedging the FSM.
//
// Synthesis Hygiene: ZERO latches, ZERO combinational '/', ZERO Verilator -Wall warnings.
`timescale 1ns/1ps

module uart_axi_regmap #(
    parameter [15:0] DEFAULT_BAUD_DIV = 16'd868 // 100 MHz / 115200 baud = 868.06
) (
    input  wire        clk,
    input  wire        rst_n,

    // Configurable baud divider (clocks per bit; 0 selects DEFAULT_BAUD_DIV)
    input  wire [15:0] cfg_baud_div,

    // Physical UART 8N1 pins
    input  wire        uart_rx,
    output reg         uart_tx,

    // AXI4-Lite Master Interface (16-bit address, 32-bit data)
    output reg  [15:0] m_axil_awaddr,
    output reg         m_axil_awvalid,
    input  wire        m_axil_awready,

    output reg  [31:0] m_axil_wdata,
    output reg  [3:0]  m_axil_wstrb,
    output reg         m_axil_wvalid,
    input  wire        m_axil_wready,

    input  wire [1:0]  m_axil_bresp,
    input  wire        m_axil_bvalid,
    output reg         m_axil_bready,

    output reg  [15:0] m_axil_araddr,
    output reg         m_axil_arvalid,
    input  wire        m_axil_arready,

    input  wire [31:0] m_axil_rdata,
    input  wire [1:0]  m_axil_rresp,
    input  wire        m_axil_rvalid,
    output reg         m_axil_rready,

    // Status telemetry
    output wire        bridge_busy,
    output reg  [15:0] rx_frame_err_cnt
);
    // Effective baud divider (minimum 4 clocks/bit for clean mid-bit sampling)
    wire [15:0] baud_raw = (cfg_baud_div == 16'd0) ? DEFAULT_BAUD_DIV : cfg_baud_div;
    wire [15:0] baud_div = (baud_raw < 16'd4) ? 16'd4 : baud_raw;
    wire [15:0] half_div = {1'b0, baud_div[15:1]};

    // -----------------------------------------------------------------------
    // 1. UART 8N1 Receiver (2-FF input sync + mid-bit sampling)
    // -----------------------------------------------------------------------
    localparam [1:0] RX_IDLE  = 2'd0;
    localparam [1:0] RX_START = 2'd1;
    localparam [1:0] RX_DATA  = 2'd2;
    localparam [1:0] RX_STOP  = 2'd3;

    reg        rx_sync1;
    reg        rx_sync2;
    reg [1:0]  rx_state;
    reg [15:0] rx_cnt;
    reg [2:0]  rx_bit_idx;
    reg [7:0]  rx_shift;
    reg        rx_byte_valid;
    reg [7:0]  rx_byte_data;

    always @(posedge clk) begin
        if (!rst_n) begin
            rx_sync1         <= 1'b1;
            rx_sync2         <= 1'b1;
            rx_state         <= RX_IDLE;
            rx_cnt           <= 16'd0;
            rx_bit_idx       <= 3'd0;
            rx_shift         <= 8'd0;
            rx_byte_valid    <= 1'b0;
            rx_byte_data     <= 8'd0;
            rx_frame_err_cnt <= 16'd0;
        end else begin
            rx_sync1      <= uart_rx;
            rx_sync2      <= rx_sync1;
            rx_byte_valid <= 1'b0;

            case (rx_state)
                RX_IDLE: begin
                    rx_cnt <= 16'd0;
                    if (!rx_sync2) begin
                        rx_state <= RX_START;
                    end
                end

                RX_START: begin
                    if (rx_cnt >= (half_div - 16'd1)) begin
                        rx_cnt <= 16'd0;
                        if (!rx_sync2) begin
                            rx_bit_idx <= 3'd0;
                            rx_state   <= RX_DATA;
                        end else begin
                            rx_state <= RX_IDLE; // false start glitch
                        end
                    end else begin
                        rx_cnt <= rx_cnt + 16'd1;
                    end
                end

                RX_DATA: begin
                    if (rx_cnt >= (baud_div - 16'd1)) begin
                        rx_cnt   <= 16'd0;
                        rx_shift <= {rx_sync2, rx_shift[7:1]};
                        if (rx_bit_idx == 3'd7) begin
                            rx_state <= RX_STOP;
                        end else begin
                            rx_bit_idx <= rx_bit_idx + 3'd1;
                        end
                    end else begin
                        rx_cnt <= rx_cnt + 16'd1;
                    end
                end

                RX_STOP: begin
                    if (rx_cnt >= (baud_div - 16'd1)) begin
                        rx_cnt   <= 16'd0;
                        rx_state <= RX_IDLE;
                        if (rx_sync2) begin
                            rx_byte_valid <= 1'b1;
                            rx_byte_data  <= rx_shift;
                        end else begin
                            rx_frame_err_cnt <= rx_frame_err_cnt + 16'd1;
                        end
                    end else begin
                        rx_cnt <= rx_cnt + 16'd1;
                    end
                end

                default: begin
                    rx_state <= RX_IDLE;
                end
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // 2. UART 8N1 Transmitter
    // -----------------------------------------------------------------------
    localparam [1:0] TX_IDLE  = 2'd0;
    localparam [1:0] TX_START = 2'd1;
    localparam [1:0] TX_DATA  = 2'd2;
    localparam [1:0] TX_STOP  = 2'd3;

    reg [1:0]  tx_state;
    reg [15:0] tx_cnt;
    reg [2:0]  tx_bit_idx;
    reg [7:0]  tx_shift;
    reg        tx_start_req;
    reg [7:0]  tx_start_byte;
    wire       tx_busy = (tx_state != TX_IDLE);

    always @(posedge clk) begin
        if (!rst_n) begin
            tx_state   <= TX_IDLE;
            tx_cnt     <= 16'd0;
            tx_bit_idx <= 3'd0;
            tx_shift   <= 8'd0;
            uart_tx    <= 1'b1;
        end else begin
            case (tx_state)
                TX_IDLE: begin
                    uart_tx <= 1'b1;
                    tx_cnt  <= 16'd0;
                    if (tx_start_req) begin
                        tx_shift <= tx_start_byte;
                        uart_tx  <= 1'b0; // start bit
                        tx_state <= TX_START;
                    end
                end

                TX_START: begin
                    uart_tx <= 1'b0;
                    if (tx_cnt >= (baud_div - 16'd1)) begin
                        tx_cnt     <= 16'd0;
                        tx_bit_idx <= 3'd0;
                        uart_tx    <= tx_shift[0];
                        tx_state   <= TX_DATA;
                    end else begin
                        tx_cnt <= tx_cnt + 16'd1;
                    end
                end

                TX_DATA: begin
                    uart_tx <= tx_shift[0];
                    if (tx_cnt >= (baud_div - 16'd1)) begin
                        tx_cnt <= 16'd0;
                        if (tx_bit_idx == 3'd7) begin
                            uart_tx  <= 1'b1; // stop bit
                            tx_state <= TX_STOP;
                        end else begin
                            tx_bit_idx <= tx_bit_idx + 3'd1;
                            tx_shift   <= {1'b0, tx_shift[7:1]};
                            uart_tx    <= tx_shift[1];
                        end
                    end else begin
                        tx_cnt <= tx_cnt + 16'd1;
                    end
                end

                TX_STOP: begin
                    uart_tx <= 1'b1;
                    if (tx_cnt >= (baud_div - 16'd1)) begin
                        tx_cnt   <= 16'd0;
                        tx_state <= TX_IDLE;
                    end else begin
                        tx_cnt <= tx_cnt + 16'd1;
                    end
                end

                default: begin
                    uart_tx  <= 1'b1;
                    tx_state <= TX_IDLE;
                end
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // 3. Framed Command Parser & AXI4-Lite Master FSM
    // -----------------------------------------------------------------------
    localparam [3:0] P_IDLE      = 4'd0;
    localparam [3:0] P_ADDR_HI   = 4'd1;
    localparam [3:0] P_ADDR_LO   = 4'd2;
    localparam [3:0] P_WDATA3    = 4'd3;
    localparam [3:0] P_WDATA2    = 4'd4;
    localparam [3:0] P_WDATA1    = 4'd5;
    localparam [3:0] P_WDATA0    = 4'd6;
    localparam [3:0] P_AXI_WR    = 4'd7;
    localparam [3:0] P_AXI_BRESP = 4'd8;
    localparam [3:0] P_AXI_AR    = 4'd9;
    localparam [3:0] P_AXI_RDATA = 4'd10;
    localparam [3:0] P_TX_SEND   = 4'd11;
    localparam [3:0] P_TX_WAIT   = 4'd12;

    localparam [7:0] CMD_WRITE = 8'h57; // 'W'
    localparam [7:0] CMD_READ  = 8'h52; // 'R'
    localparam [7:0] RSP_OK    = 8'h4B; // 'K'
    localparam [7:0] RSP_ERR   = 8'h45; // 'E'
    localparam [7:0] RSP_DATA  = 8'h44; // 'D'

    reg [3:0]  p_state;
    reg        is_write_cmd;
    reg [15:0] cmd_addr;
    reg [23:0] cmd_wdata_hi;
    reg [7:0]  tx_buf [0:4];
    reg [2:0]  tx_len;
    reg [2:0]  tx_idx;
    reg        aw_done;
    reg        w_done;

    assign bridge_busy = (p_state != P_IDLE) || tx_busy;

    // Sink unused rresp bits cleanly (AXI4-Lite slave always returns OKAY or SLVERR)
    wire _unused_ok = &{1'b0, m_axil_rresp[1:0]};

    always @(posedge clk) begin
        if (!rst_n) begin
            p_state        <= P_IDLE;
            is_write_cmd   <= 1'b0;
            cmd_addr       <= 16'd0;
            cmd_wdata_hi   <= 24'd0;
            tx_buf[0]      <= 8'd0;
            tx_buf[1]      <= 8'd0;
            tx_buf[2]      <= 8'd0;
            tx_buf[3]      <= 8'd0;
            tx_buf[4]      <= 8'd0;
            tx_len         <= 3'd0;
            tx_idx         <= 3'd0;
            tx_start_req   <= 1'b0;
            tx_start_byte  <= 8'd0;
            aw_done        <= 1'b0;
            w_done         <= 1'b0;
            m_axil_awaddr  <= 16'd0;
            m_axil_awvalid <= 1'b0;
            m_axil_wdata   <= 32'd0;
            m_axil_wstrb   <= 4'hF;
            m_axil_wvalid  <= 1'b0;
            m_axil_bready  <= 1'b0;
            m_axil_araddr  <= 16'd0;
            m_axil_arvalid <= 1'b0;
            m_axil_rready  <= 1'b0;
        end else begin
            tx_start_req <= 1'b0;

            case (p_state)
                P_IDLE: begin
                    m_axil_awvalid <= 1'b0;
                    m_axil_wvalid  <= 1'b0;
                    m_axil_bready  <= 1'b0;
                    m_axil_arvalid <= 1'b0;
                    m_axil_rready  <= 1'b0;
                    if (rx_byte_valid) begin
                        if (rx_byte_data == CMD_WRITE) begin
                            is_write_cmd <= 1'b1;
                            p_state      <= P_ADDR_HI;
                        end else if (rx_byte_data == CMD_READ) begin
                            is_write_cmd <= 1'b0;
                            p_state      <= P_ADDR_HI;
                        end
                    end
                end

                P_ADDR_HI: begin
                    if (rx_byte_valid) begin
                        cmd_addr[15:8] <= rx_byte_data;
                        p_state        <= P_ADDR_LO;
                    end
                end

                P_ADDR_LO: begin
                    if (rx_byte_valid) begin
                        cmd_addr[7:0] <= rx_byte_data;
                        if (is_write_cmd) begin
                            p_state <= P_WDATA3;
                        end else begin
                            m_axil_araddr  <= {cmd_addr[15:8], rx_byte_data};
                            m_axil_arvalid <= 1'b1;
                            p_state        <= P_AXI_AR;
                        end
                    end
                end

                P_WDATA3: begin
                    if (rx_byte_valid) begin
                        cmd_wdata_hi[23:16] <= rx_byte_data;
                        p_state             <= P_WDATA2;
                    end
                end

                P_WDATA2: begin
                    if (rx_byte_valid) begin
                        cmd_wdata_hi[15:8] <= rx_byte_data;
                        p_state            <= P_WDATA1;
                    end
                end

                P_WDATA1: begin
                    if (rx_byte_valid) begin
                        cmd_wdata_hi[7:0] <= rx_byte_data;
                        p_state           <= P_WDATA0;
                    end
                end

                P_WDATA0: begin
                    if (rx_byte_valid) begin
                        m_axil_awaddr  <= cmd_addr;
                        m_axil_awvalid <= 1'b1;
                        m_axil_wdata   <= {cmd_wdata_hi, rx_byte_data};
                        m_axil_wstrb   <= 4'hF;
                        m_axil_wvalid  <= 1'b1;
                        aw_done        <= 1'b0;
                        w_done         <= 1'b0;
                        p_state        <= P_AXI_WR;
                    end
                end

                P_AXI_WR: begin
                    if (m_axil_awvalid && m_axil_awready) begin
                        m_axil_awvalid <= 1'b0;
                        aw_done        <= 1'b1;
                    end
                    if (m_axil_wvalid && m_axil_wready) begin
                        m_axil_wvalid <= 1'b0;
                        w_done        <= 1'b1;
                    end
                    if ((aw_done || (m_axil_awvalid && m_axil_awready)) &&
                        (w_done  || (m_axil_wvalid  && m_axil_wready))) begin
                        m_axil_bready <= 1'b1;
                        p_state       <= P_AXI_BRESP;
                    end
                end

                P_AXI_BRESP: begin
                    if (m_axil_bvalid && m_axil_bready) begin
                        m_axil_bready <= 1'b0;
                        tx_buf[0]     <= (m_axil_bresp == 2'b00) ? RSP_OK : RSP_ERR;
                        tx_len        <= 3'd1;
                        tx_idx        <= 3'd0;
                        p_state       <= P_TX_SEND;
                    end
                end

                P_AXI_AR: begin
                    if (m_axil_arvalid && m_axil_arready) begin
                        m_axil_arvalid <= 1'b0;
                        m_axil_rready  <= 1'b1;
                        p_state        <= P_AXI_RDATA;
                    end
                end

                P_AXI_RDATA: begin
                    if (m_axil_rvalid && m_axil_rready) begin
                        m_axil_rready <= 1'b0;
                        tx_buf[0]     <= RSP_DATA;
                        tx_buf[1]     <= m_axil_rdata[31:24];
                        tx_buf[2]     <= m_axil_rdata[23:16];
                        tx_buf[3]     <= m_axil_rdata[15:8];
                        tx_buf[4]     <= m_axil_rdata[7:0];
                        tx_len        <= 3'd5;
                        tx_idx        <= 3'd0;
                        p_state       <= P_TX_SEND;
                    end
                end

                P_TX_SEND: begin
                    if (!tx_busy) begin
                        tx_start_req  <= 1'b1;
                        tx_start_byte <= tx_buf[tx_idx];
                        p_state       <= P_TX_WAIT;
                    end
                end

                P_TX_WAIT: begin
                    // Wait 1 cycle for tx_busy to assert, then wait until TX finishes
                    if (!tx_start_req && !tx_busy) begin
                        if ((tx_idx + 3'd1) >= tx_len) begin
                            p_state <= P_IDLE;
                        end else begin
                            tx_idx  <= tx_idx + 3'd1;
                            p_state <= P_TX_SEND;
                        end
                    end
                end

                default: begin
                    p_state <= P_IDLE;
                end
            endcase
        end
    end
endmodule
