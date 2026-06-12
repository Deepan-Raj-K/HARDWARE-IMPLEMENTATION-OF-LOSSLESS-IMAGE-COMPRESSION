module rice_encoder #(parameter int BPP = 8, U_W = BPP+1, K_W = $clog2(U_W+1))(
	input  logic           clk,
	input  logic           rst_n,
	input  logic [K_W-1:0] k,
	input  logic [U_W-1:0] U_in,
	input  logic           U_valid,
	output logic           bit_valid,
	output logic           bit_out,
	output logic           enc_busy
);
	typedef enum logic [1:0] {
		IDLE  = 2'd0,
		UNARY = 2'd1,
		STOP  = 2'd2,
		REM   = 2'd3
	} state_t;
	state_t state;
	logic [U_W-1:0] U_reg;
	logic [K_W-1:0] k_reg;
	logic [U_W-1:0] unary_count;
	logic [K_W-1:0] rem_count;
	logic [U_W-1:0] r_reg;
	assign enc_busy = (state != IDLE);
	always_ff @(posedge clk or negedge rst_n) begin
		if (!rst_n) begin
			state <= IDLE;
			bit_valid <= 1'b0;
			bit_out <= 1'b0;
			U_reg <= '0;
			k_reg <= '0;
			unary_count <= '0;
			rem_count <= '0;
			r_reg <= '0;
		end
		else begin
			bit_valid <= 1'b0;
			case (state)
				IDLE: begin
					if (U_valid) begin
						U_reg <= U_in;
						k_reg <= k;
						unary_count <= (U_in >> k);
						r_reg <= U_in & ((1 << k) - 1);
						rem_count <= k;
						state <= UNARY;
					end
				end
				UNARY: begin
					if (unary_count != 0) begin
						bit_out <= 1'b1;
						bit_valid <= 1'b1;
						unary_count <= unary_count - 1;
					end
					else begin
						state <= STOP;
					end
				end
				STOP: begin
					bit_out <= 1'b0;
					bit_valid <= 1'b1;
					state <= REM;
				end
				REM: begin
					if (rem_count != 0) begin
						bit_out   <= r_reg[rem_count-1];
						bit_valid <= 1'b1;
						rem_count <= rem_count - 1;
					end
					else begin
						state <= IDLE;
					end
				end
				default: state <= IDLE;
			endcase
		end
	end
endmodule