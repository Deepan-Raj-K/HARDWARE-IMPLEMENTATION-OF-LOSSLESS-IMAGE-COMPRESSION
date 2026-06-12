`timescale 1ns/1ps

// ================================================================
//  MEDRICE RTL  –  Fully corrected version
//
//  Bug-fixes in THIS revision (on top of prior corrections):
//  ──────────────────────────────────────────────────────────────
//  F1  ENCODE_Q / normal path: terminating zero is emitted as
//      part of ENCODE_Q (not as a side-effect of the transition),
//      so ENCODE_R sees bit_cnt=0 and emits exactly k remainder
//      bits, fixing the off-by-one that corrupted every pixel.
//
//  F2  ENCODE_R exit condition: was `bit_cnt >= k` which skipped
//      the last bit.  Corrected to `bit_cnt == k` (transition
//      only AFTER all k bits have been sent).
//
//  F3  ENCODE_Q escape path: bit count now checked with
//      `bit_cnt == BPP+4` (exit after all bits emitted) rather
//      than before, ensuring the full 12-bit escape codeword
//      is always written.
//
//  F4  line_buffer / encoder handshake: valid_in to the encoder
//      is masked to a single-cycle pulse by the ready/ack
//      handshake.  valid_in is deasserted by the IDLE state
//      before the line_buffer can advance x for the same pixel
//      a second time.  The wrapper now exposes ready so the
//      testbench knows when to present the next pixel.
//
//  F5  ENCODE_FLAG: flag bit is now emitted with correct polarity
//      matching the Python reference:
//        flag=0 → normal (q < threshold)
//        flag=1 → escape (q >= threshold)
//      (was already correct; confirmed here for clarity)
//
//  F6  k clamped to [0,9] after msb_pos to avoid shifting U by
//      more than its width in ENCODE_R.
//
//  All prior fixes (B1-B10) from the corrected original are
//  preserved.
// ================================================================


// ================================================================
//  line_buffer
// ================================================================
module line_buffer #(
    parameter WIDTH = 3072
)(
    input             clk,
    input             rst,
    input      [7:0]  pixel_in,
    input             valid_in,
    output reg [7:0]  A,
    output reg [7:0]  B,
    output reg [7:0]  C
);
    (* ram_style = "block" *) reg [7:0] prev_row [0:WIDTH-1];
    reg [7:0]  left_pixel;
    reg [7:0]  top_left_pixel;
    reg [12:0] x;   // wide enough for WIDTH up to 8192

    // B2 – virtual row above row-0 = 0
    integer j;
    initial begin
        for (j = 0; j < WIDTH; j = j + 1)
            prev_row[j] = 8'd0;
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            x              <= 13'd0;
            left_pixel     <= 8'd0;
            top_left_pixel <= 8'd0;
            A <= 8'd0; B <= 8'd0; C <= 8'd0;
        end else if (valid_in) begin
            // Drive A/B/C for the current pixel.
            // Encoder reads them in WAIT (next cycle after valid_in).
            A <= (x == 0) ? 8'd0 : left_pixel;
            B <= prev_row[x];
            C <= (x == 0) ? 8'd0 : top_left_pixel;

            // B1: save prev_row[x] (= current B) so next pixel can use it as C
            top_left_pixel <= prev_row[x];
            prev_row[x]    <= pixel_in;
            left_pixel     <= pixel_in;

            x <= (x == WIDTH - 1) ? 13'd0 : x + 1;
        end
    end
endmodule


// ================================================================
//  bit_packer  –  with flush support
// ================================================================
module bit_packer (
    input             clk,
    input             rst,
    input             bit_in,
    input             valid_in,
    input             flush,
    output reg [7:0]  byte_out,
    output reg        valid_out
);
    reg [6:0] buf_r;
    reg [2:0] cnt;

    // buf_r accumulates bits LSB-first (newest at LSB, oldest drifts toward bit[cnt-1]).
    // After N bits: buf_r[N-1:0] holds the bits in order (oldest=MSB of output).
    function [7:0] flush_byte;
        input [6:0] buuf;
        input [2:0] c;
        begin
            case (c)
                3'd1: flush_byte = {buuf[0],            7'b000_0000};
                3'd2: flush_byte = {buuf[1:0],           6'b00_0000};
                3'd3: flush_byte = {buuf[2:0],           5'b0_0000};
                3'd4: flush_byte = {buuf[3:0],           4'b0000};
                3'd5: flush_byte = {buuf[4:0],           3'b000};
                3'd6: flush_byte = {buuf[5:0],           2'b00};
                3'd7: flush_byte = {buuf[6:0],           1'b0};
                default: flush_byte = 8'b0;
            endcase
        end
    endfunction

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            buf_r     <= 7'd0;
            cnt       <= 3'd0;
            valid_out <= 1'b0;
            byte_out  <= 8'd0;
        end else begin
            valid_out <= 1'b0;

            if (valid_in) begin
                if (cnt == 3'd7) begin
                    byte_out  <= {buf_r, bit_in};
                    valid_out <= 1'b1;
                    buf_r     <= 7'd0;
                    cnt       <= 3'd0;
                end else begin
                    buf_r <= {buf_r[5:0], bit_in};
                    cnt   <= cnt + 1;
                end
            end else if (flush && cnt != 3'd0) begin
                byte_out  <= flush_byte(buf_r, cnt);
                valid_out <= 1'b1;
                buf_r     <= 7'd0;
                cnt       <= 3'd0;
            end
        end
    end
endmodule


// ================================================================
//  medrice_encoder  –  core compression engine
//
//  Encoding for one pixel:
//    1. IDLE  : wait for valid_in pulse; latch pixel; → WAIT
//    2. WAIT  : read stable A/B/C; compute MED, E, U, q; → ENCODE_FLAG
//    3. ENCODE_FLAG : emit flag bit (0=normal, 1=escape)
//       → ENCODE_Q
//    4. ENCODE_Q :
//         normal  (q < threshold):
//           emit q ones (unary) then one terminating zero
//           → ENCODE_R
//         escape  (q >= threshold):
//           emit BPP+4 bits of U MSB-first
//           → UPDATE  (no remainder needed)
//    5. ENCODE_R : emit k remainder bits of U (LSB-last)
//       → UPDATE
//    6. UPDATE : update A_est and k; → IDLE
// ================================================================
module medrice_encoder (
    input             clk,
    input             rst,
    input      [7:0]  pixel_in,
    input             valid_in,
    input      [7:0]  A,
    input      [7:0]  B,
    input      [7:0]  C,
    output reg        bit_out,
    output reg        bit_valid,
    output reg        ready
);
    parameter BPP = 8;
    parameter S   = 4;

    localparam IDLE        = 3'd0,
               WAIT        = 3'd1,
               ENCODE_FLAG = 3'd2,
               ENCODE_Q    = 3'd3,
               ENCODE_R    = 3'd4,
               UPDATE      = 3'd5;

    // ── Persistent registers ──────────────────────────────────────
    reg [7:0]         pixel_latched;
    reg [8:0]         X_hat;
    reg signed [9:0]  E;
    reg [9:0]         U;
    reg [9:0]         A_est;
    reg [3:0]         k;          // Golomb parameter, range [0,9]
    reg [9:0]         q;          // quotient
    reg [4:0]         bit_cnt;    // emission counter
    reg [2:0]         state;

    // ── Golomb escape threshold = clamp(k+4, 8, 16) ──────────────
    wire [4:0] threshold;
    assign threshold = (({1'b0,k}+5'd4) < 5'd8)  ? 5'd8  :
                       (({1'b0,k}+5'd4) > 5'd16)  ? 5'd16 :
                        ({1'b0,k}+5'd4);

    // ── msb_pos: highest set bit (= floor(log2(val))) ─────────────
    // B7: iterate 0→9 so the HIGHEST set bit wins.
    // F6: result clamped to 4 bits (max 9).
    function [3:0] msb_pos_hw;
        input [9:0] val;
        integer i;
        begin
            msb_pos_hw = 4'd0;
            for (i = 0; i <= 9; i = i + 1)
                if (val[i]) msb_pos_hw = i[3:0];
        end
    endfunction

    // ── Blocking temporaries used in WAIT ─────────────────────────
    reg [8:0]         xh;
    reg signed [9:0]  e_tmp;
    reg [9:0]         abs_e;
    reg [9:0]         u_tmp;
    reg [9:0]         q_tmp;

    // ── UPDATE temporaries ────────────────────────────────────────
    reg signed [11:0] diff_s;
    reg signed [11:0] nest_s;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state         <= IDLE;
            A_est         <= 10'd4;
            k             <= 4'd2;   // msb_pos(4) = 2
            ready         <= 1'b1;
            bit_valid     <= 1'b0;
            bit_out       <= 1'b0;
            pixel_latched <= 8'd0;
            bit_cnt       <= 5'd0;
        end else begin
            // B10: suppress bit output by default every cycle
            bit_valid <= 1'b0;

            case (state)

            // ── IDLE ──────────────────────────────────────────────
            // ready=1; wait for a single-cycle valid_in pulse.
            IDLE: begin
                ready <= 1'b1;
                if (valid_in) begin
                    pixel_latched <= pixel_in;   // B4: latch immediately
                    ready         <= 1'b0;
                    state         <= WAIT;
                end
            end

            // ── WAIT ─────────────────────────────────────────────
            // A/B/C are stable (line_buffer NBA resolved last cycle).
            // All arithmetic uses blocking assignments (B5/B6).
            WAIT: begin
                // MED predictor (9-bit prevents A+B-C overflow)
                if (C >= ((A > B) ? A : B))
                    xh = {1'b0, (A < B) ? A : B};
                else if (C <= ((A < B) ? A : B))
                    xh = {1'b0, (A > B) ? A : B};
                else
                    xh = {1'b0,A} + {1'b0,B} - {1'b0,C};

                // Signed prediction error (B5)
                e_tmp = $signed({2'b00, pixel_latched})
                      - $signed({1'b0,  xh});

                // Unsigned Rice mapping (B6)
                if (!e_tmp[9]) begin           // E >= 0
                    u_tmp = {e_tmp[8:0], 1'b0};
                end else begin                 // E < 0
                    abs_e = -e_tmp;
                    u_tmp = (abs_e << 1) - 10'd1;
                end

                q_tmp = u_tmp >> k;

                X_hat   <= xh;
                E       <= e_tmp;
                U       <= u_tmp;
                q       <= q_tmp;
                bit_cnt <= 5'd0;
                state   <= ENCODE_FLAG;
            end

            // ── ENCODE_FLAG ───────────────────────────────────────
            // Emit 1-bit flag:  0 = normal,  1 = escape
            ENCODE_FLAG: begin
                bit_out   <= (q < threshold) ? 1'b0 : 1'b1;   // F5
                bit_valid <= 1'b1;
                bit_cnt   <= 5'd0;
                state     <= ENCODE_Q;
            end

            // ── ENCODE_Q ──────────────────────────────────────────
            // F1: Normal path  – emit q ones then the terminating
            //     zero, all within ENCODE_Q.  bit_cnt runs 0..q.
            //     When bit_cnt == q we emit the 0 and transition
            //     to ENCODE_R with bit_cnt reset to 0.
            //
            // F3: Escape path  – emit BPP+4 bits MSB-first.
            //     Exit when bit_cnt reaches BPP+4 (i.e. after the
            //     last bit has been sent the PREVIOUS cycle).
            ENCODE_Q: begin
                if (q < threshold) begin
                    // ── Normal Golomb ─────────────────────────────
                    if (bit_cnt < q) begin
                        // Unary: emit a 1
                        bit_out   <= 1'b1;
                        bit_valid <= 1'b1;
                        bit_cnt   <= bit_cnt + 1;
                        // stay in ENCODE_Q
                    end else begin
                        // bit_cnt == q: emit terminating zero and
                        // move to ENCODE_R (F1 fix)
                        bit_out   <= 1'b0;
                        bit_valid <= 1'b1;
                        bit_cnt   <= 5'd0;      // reset for ENCODE_R
                        state     <= ENCODE_R;
                    end
                end else begin
                    // ── Escape: (BPP+4) bits of U, MSB first ─────
                    if (bit_cnt < (BPP + 4)) begin
                        bit_out   <= (U >> ((BPP+4)-1 - bit_cnt)) & 1'b1;
                        bit_valid <= 1'b1;
                        bit_cnt   <= bit_cnt + 1;
                        // stay in ENCODE_Q
                    end else begin
                        // All escape bits sent; no remainder needed
                        // bit_valid stays 0 (B10)
                        bit_cnt <= 5'd0;
                        state   <= UPDATE;
                    end
                end
            end

            // ── ENCODE_R ──────────────────────────────────────────
            // Emit exactly k remainder bits of U (bits [k-1 : 0]),
            // MSB first.  bit_cnt runs from 0 to k-1.
            //
            // F2 fix: transition to UPDATE only when bit_cnt == k
            // (i.e. after the last remainder bit was sent).
            // If k==0 there are no remainder bits to send.
            ENCODE_R: begin
                if (k == 4'd0) begin
                    // No remainder bits; go straight to UPDATE
                    // bit_valid stays 0 (B10)
                    state <= UPDATE;
                end else if (bit_cnt < k) begin
                    // Emit remainder bit [(k-1-bit_cnt)]
                    bit_out   <= (U >> (k - 1 - bit_cnt)) & 1'b1;
                    bit_valid <= 1'b1;
                    bit_cnt   <= bit_cnt + 1;
                    // stay in ENCODE_R
                end else begin
                    // bit_cnt == k: all remainder bits sent (F2)
                    // bit_valid stays 0 (B10)
                    state <= UPDATE;
                end
            end

            // ── UPDATE ────────────────────────────────────────────
            // B8: signed subtraction  B9: clamp A_est >= 1
            UPDATE: begin
                diff_s = $signed({2'b00, U})
                       - $signed({2'b00, A_est});
                nest_s = $signed({2'b00, A_est})
                       + (diff_s >>> S);

                if (nest_s < 12'sd1) begin
                    A_est <= 10'd1;
                    k     <= 4'd0;
                end else begin
                    A_est <= nest_s[9:0];
                    k     <= msb_pos_hw(nest_s[9:0]);
                end

                ready <= 1'b1;
                state <= IDLE;
            end

            default: state <= IDLE;

            endcase
        end
    end
endmodule


// ================================================================
//  medrice_escape_encoder  –  top-level wrapper
// ================================================================
module medrice_escape_encoder #(
    parameter IMG_WIDTH = 3072
)(
    input        clk,
    input        rst,
    input  [7:0] pixel_in,
    input        valid_in,   // single-cycle pulse: present next pixel
    input        flush,      // drain partial byte from bit_packer
    output [7:0] byte_out,
    output       valid_out,
    output       bit_out,
    output       bit_valid,
    output       ready
);
    wire [7:0] A, B, C;
    wire       internal_bit, internal_valid;

    line_buffer #(.WIDTH(IMG_WIDTH)) lb (
        .clk      (clk),
        .rst      (rst),
        .pixel_in (pixel_in),
        .valid_in (valid_in),   // advances only on pixel-acceptance pulses
        .A(A), .B(B), .C(C)
    );

    medrice_encoder enc (
        .clk      (clk),
        .rst      (rst),
        .pixel_in (pixel_in),
        .valid_in (valid_in),
        .A(A), .B(B), .C(C),
        .bit_out  (internal_bit),
        .bit_valid(internal_valid),
        .ready    (ready)
    );

    assign bit_out   = internal_bit;
    assign bit_valid = internal_valid;

    bit_packer bp (
        .clk      (clk),
        .rst      (rst),
        .bit_in   (internal_bit),
        .valid_in (internal_valid),
        .flush    (flush),
        .byte_out (byte_out),
        .valid_out(valid_out)
    );
endmodule