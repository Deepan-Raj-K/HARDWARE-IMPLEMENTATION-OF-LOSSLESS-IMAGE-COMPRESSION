module medrice_decoder (
    input        clk,
    input        rst,

    input        bit_in,
    input        bit_valid,

    input  [7:0] A,
    input  [7:0] B,
    input  [7:0] C,

    output reg [7:0] pixel_out,
    output reg       valid_out,
    output reg       ready
);

    parameter BPP = 8;
    parameter S   = 4;

    localparam IDLE        = 0,
               READ_FLAG   = 1,
               READ_Q      = 2,
               READ_R      = 3,
               READ_ESC    = 4,
               RECONSTRUCT = 5,
               UPDATE      = 6;

    reg [2:0] state;

    reg [9:0] U;
    reg [9:0] q;
    reg [3:0] k;
    reg [9:0] A_est;

    reg [4:0] bit_cnt;
    reg [4:0] threshold;

    reg flag;

    // predictor
    reg [8:0] X_hat;
    reg signed [9:0] E;
	 
	 reg signed [11:0] diff;
    reg signed [11:0] nextA;

    // --------------------------
    // msb_pos
    // --------------------------
    function [3:0] msb_pos_hw;
        input [9:0] val;
        integer i;
        begin
            msb_pos_hw = 0;
            for (i = 0; i <= 9; i = i + 1)
                if (val[i]) msb_pos_hw = i;
        end
    endfunction

    // --------------------------
    // threshold
    // --------------------------
    always @(*) begin
        if ((k + 4) < 8) threshold = 8;
        else if ((k + 4) > 16) threshold = 16;
        else threshold = k + 4;
    end

    // --------------------------
    // FSM
    // --------------------------
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state     <= IDLE;
            ready     <= 1;
            valid_out <= 0;
            A_est     <= 4;
            k         <= 2;
        end else begin
            valid_out <= 0;

            case (state)

            IDLE: begin
                ready <= 1;
                if (bit_valid) begin
                    flag  <= bit_in;
                    q     <= 0;
                    ready <= 0;
                    state <= READ_Q;
                end
            end

            // ------------------
            // READ Q (unary)
            // ------------------
            READ_Q: begin
                if (flag == 0) begin
                    if (bit_valid) begin
                        if (bit_in == 1) begin
                            q <= q + 1;
                        end else begin
                            bit_cnt <= 0;
                            state   <= READ_R;
                        end
                    end
                end else begin
                    // escape
                    U <= 0;
                    bit_cnt <= 0;
                    state <= READ_ESC;
                end
            end

            // ------------------
            // READ remainder
            // ------------------
            READ_R: begin
                if (k == 0) begin
                    U <= q;
                    state <= RECONSTRUCT;
                end else if (bit_valid) begin
                    U <= (q << k) | (bit_in << (k-1-bit_cnt)) | (U & ((1<<(k-1-bit_cnt))-1));
                    bit_cnt <= bit_cnt + 1;

                    if (bit_cnt == k-1)
                        state <= RECONSTRUCT;
                end
            end

            // ------------------
            // ESCAPE MODE
            // ------------------
            READ_ESC: begin
                if (bit_valid) begin
                    U <= (U << 1) | bit_in;
                    bit_cnt <= bit_cnt + 1;

                    if (bit_cnt == (BPP+4-1))
                        state <= RECONSTRUCT;
                end
            end

            // ------------------
            // RECONSTRUCT PIXEL
            // ------------------
            RECONSTRUCT: begin

                // MED predictor
                if (C >= ((A > B) ? A : B))
                    X_hat = (A < B) ? A : B;
                else if (C <= ((A < B) ? A : B))
                    X_hat = (A > B) ? A : B;
                else
                    X_hat = A + B - C;

                // U → E
                if (U[0] == 0)
                    E = U >> 1;
                else
                    E = -((U + 1) >> 1);

                pixel_out <= X_hat + E;
                valid_out <= 1;

                state <= UPDATE;
            end

            // ------------------
            // UPDATE (same as encoder)
            // ------------------
            UPDATE: begin

                diff  = $signed(U) - $signed(A_est);
                nextA = $signed(A_est) + (diff >>> S);

                if (nextA < 1) begin
                    A_est <= 1;
                    k <= 0;
                end else begin
                    A_est <= nextA;
                    k <= msb_pos_hw(nextA);
                end

                ready <= 1;
                state <= IDLE;
            end

            endcase
        end
    end
endmodule