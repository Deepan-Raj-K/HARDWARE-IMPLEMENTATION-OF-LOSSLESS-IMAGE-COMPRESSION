module output_writer (
	input  logic        clk,
	input  logic        rst_n,
	input  logic        out_valid,
	input  logic [7:0]  out_byte,
	input	 logic 		  frame_start,
	output logic        wr_en,
	output logic [31:0] wr_addr,
	output logic [7:0]  wr_data
);
	always_ff @(posedge clk or negedge rst_n) begin
		if(!rst_n) begin
			wr_en <= 0;
			wr_addr <= 0;
			wr_data <= 0;
		end
		else begin
			if(frame_start)
				wr_addr <= 0;
			else if(out_valid) begin
				wr_en <= 1;
				wr_addr <= wr_addr + 1;
				wr_data <= out_byte;
			end
			else begin
				wr_en <= 0;
			end
		end
	end
endmodule