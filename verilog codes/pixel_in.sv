module pixel_in #(parameter int BPP = 8)(
	input  logic           clk,
	input  logic           rst_n,
	input  logic           in_valid,
	input  logic [BPP-1:0] in_pixel,
	output logic           px_valid,
	output logic [BPP-1:0] px_data
);
	always_ff @(posedge clk or negedge rst_n) begin
		if(!rst_n) begin
			px_valid <= 0;
			px_data <= 0;
		end
		else begin
			if(in_valid == 1) begin
				px_valid <= 1;
				px_data <= in_pixel;
			end
			else begin
				px_valid <= 0;
				px_data <= 0;
			end
		end
	end
endmodule
