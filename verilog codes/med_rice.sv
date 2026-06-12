module med_rice #(parameter int BPP = 8, W = 1920)(
    input  logic           clk,
    input  logic           rst_n,
    input  logic           in_valid,
    input  logic [BPP-1:0] in_pixel,
    input  logic           frame_start,
    input  logic           frame_end,

    output logic           wr_en,
    output logic [31:0]    wr_addr,
    output logic [7:0]     wr_data
);

    logic px_valid;
    logic [BPP-1:0] px_data;

    logic nb_valid;
    logic [BPP-1:0] A_left,B_top,C_topleft,X_cur;

    logic pred_valid;
    logic [BPP-1:0] X_hat;

    logic pred_valid_r;
    logic [BPP-1:0] X_hat_r,X_cur_r;

    logic err_valid;
    logic signed [BPP:0] E;

    logic map_valid;
    logic [BPP:0] U;

    localparam int U_W = BPP+1;
    localparam int K_W = $clog2(U_W+1);

    logic k_valid;
    logic [K_W-1:0] k_param;

    logic bit_valid;
    logic bit_out;
    logic enc_busy;

    logic encoder_ready;
    assign encoder_ready = !enc_busy;

    logic byte_valid;
    logic [7:0] byte_out;

    // -------------------------------------------------
    // Stall logic
    // -------------------------------------------------

    logic stall;
    logic U_buf_valid;

    assign stall = !encoder_ready;

    // -------------------------------------------------
    // Pixel input
    // -------------------------------------------------

	 logic px_valid_int;
	logic [BPP-1:0] px_data_int;

	assign px_valid = px_valid_int && !stall;
	assign px_data  = px_data_int;

    pixel_in #(.BPP(BPP)) u_pixel_in(
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .in_pixel(in_pixel),
        .px_valid(px_valid_int),
        .px_data(px_data_int)
    );

    // -------------------------------------------------

    line_buffer #(.BPP(BPP),.W(W)) u_line_buffer(
        .clk(clk),
        .rst_n(rst_n),
        .px_valid(px_valid),
        .px_in(px_data),
        .nb_valid(nb_valid),
        .A_left(A_left),
        .B_top(B_top),
        .C_topleft(C_topleft),
        .X_cur(X_cur)
    );

    // -------------------------------------------------

    med_predictor #(.BPP(BPP)) u_predictor(
        .nb_valid(nb_valid),
        .A(A_left),
        .B(B_top),
        .C(C_topleft),
        .pred_valid(pred_valid),
        .X_hat(X_hat)
    );

    // -------------------------------------------------

    always_ff @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            pred_valid_r <= 0;
            X_hat_r <= 0;
            X_cur_r <= 0;
        end
        else begin
            pred_valid_r <= pred_valid;
            X_hat_r <= X_hat;
            X_cur_r <= X_cur;
        end
    end

    // -------------------------------------------------

    residual_gen #(.BPP(BPP)) u_residual(
        .pred_valid(pred_valid_r),
        .X(X_cur_r),
        .X_hat(X_hat_r),
        .err_valid(err_valid),
        .E(E)
    );

    // -------------------------------------------------

    signed_mapper #(.BPP(BPP)) u_mapper(
        .err_valid(err_valid),
        .E(E),
        .map_valid(map_valid),
        .U(U)
    );
	 logic [BPP-1:0] A_r,B_r,C_r;

always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        A_r <= 0;
        B_r <= 0;
        C_r <= 0;
    end
    else if(nb_valid) begin
        A_r <= A_left;
        B_r <= B_top;
        C_r <= C_topleft;
    end
end
	 always @(posedge clk)
if(map_valid)
$display("PIX=%0d A=%0d B=%0d C=%0d PRED=%0d ERR=%0d U=%0d k=%0d",
    X_cur_r,
    A_r,
    B_r,
    C_r,
    X_hat_r,
    E,
    U,
    k_param
);

    logic map_valid_gated;
    assign map_valid_gated = map_valid && !stall;

    // -------------------------------------------------

    k_estimator #(.BPP(BPP)) u_k_estimator(
        .clk(clk),
        .rst_n(rst_n),
        .map_valid(map_valid_gated),
        .U(U),
        .k_valid(k_valid),
        .k_param(k_param)
    );

    // -------------------------------------------------
    // U buffer
    // -------------------------------------------------

    logic [U_W-1:0] U_buf;
    logic [K_W-1:0] k_buf;

    always_ff @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            U_buf_valid <= 0;
            U_buf <= 0;
            k_buf <= 0;
        end
        else begin

            if(k_valid && !U_buf_valid) begin
                U_buf <= U;
                k_buf <= k_param;
                U_buf_valid <= 1;
            end

            else if(U_buf_valid && encoder_ready) begin
                U_buf_valid <= 0;
            end

        end
    end

    // -------------------------------------------------
    // Rice encoder
    // -------------------------------------------------

    rice_encoder #(.BPP(BPP)) u_rice_encoder(
        .clk(clk),
        .rst_n(rst_n),
        .k(k_buf),
        .U_in(U_buf),
        .U_valid(U_buf_valid),
        .bit_valid(bit_valid),
        .bit_out(bit_out),
        .enc_busy(enc_busy)
    );

    // -------------------------------------------------
    // Bit packer
    // -------------------------------------------------

    bit_packer u_bit_packer(
        .clk(clk),
        .rst_n(rst_n),
        .bit_valid(bit_valid),
        .bit_in(bit_out),
        .flush(frame_end && !enc_busy),
        .byte_valid(byte_valid),
        .byte_out(byte_out)
    );

    // -------------------------------------------------

    output_writer u_output_writer(
        .clk(clk),
        .rst_n(rst_n),
        .out_valid(byte_valid),
        .out_byte(byte_out),
        .frame_start(frame_start),
        .wr_en(wr_en),
        .wr_addr(wr_addr),
        .wr_data(wr_data)
    );

endmodule