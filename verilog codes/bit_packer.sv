module bit_packer (
	input  logic       clk,
	input  logic       rst_n,
	input  logic       bit_valid,
	input  logic       bit_in,
	input  logic 		 flush,
	output logic       byte_valid,
	output logic [7:0] byte_out
);
	logic [3:0] cnt;
	logic [7:0] shift_reg;
	always_ff @(posedge clk or negedge rst_n) begin
		if (!rst_n) begin
			shift_reg  <= 0;
			byte_out <= 0;
			cnt <= 0;
			byte_valid <= 0;
		end
		else begin
			byte_valid <= 0;
			if(bit_valid) begin
				shift_reg <= {shift_reg[6:0], bit_in};
				cnt <= cnt + 1;	
				if(cnt == 4'd7) begin
					byte_out <= {shift_reg[6:0], bit_in};
					byte_valid <= 1;
					cnt <= 0;
				end
			end
			else if(flush && cnt != 0) begin
				byte_valid <= 1;
				byte_out <= shift_reg << (8 - cnt);
				cnt <= 0;
			end
		end
	end
endmodule