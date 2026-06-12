module line_buffer #(parameter int BPP = 8, W = 1920)(
	input  logic           clk,
	input  logic           rst_n,
	input  logic           px_valid,
	input  logic [BPP-1:0] px_in,
	output logic           nb_valid,
	output logic [BPP-1:0] A_left,
	output logic [BPP-1:0] B_top,
	output logic [BPP-1:0] C_topleft,
	output logic [BPP-1:0] X_cur
);
	logic [BPP-1:0]       px_buff;
	logic [BPP-1:0]       line_buff     [0:W-1];
	logic [BPP-1:0]       line_buff_cur [0:W-1];
	logic [$clog2(W)-1:0] col;
	logic                 prev_row_valid;
	logic                 row_sel;
	logic [BPP-1:0]       prev_row_pixel_s0;
	logic [$clog2(W)-1:0] col_s0;
	logic                 first_col_s0;
	logic                 prev_row_valid_s0;
	logic [BPP-1:0]       prev_row_pixel_s1;
	logic [BPP-1:0]       prev_row_pixel_left_s1;
	logic [BPP-1:0]       px_buff_s1;
	logic [$clog2(W)-1:0] col_s1;
	logic                 first_col_s1;
	logic                 prev_row_valid_s1;
	always_ff @(posedge clk or negedge rst_n) begin
		if(!rst_n) begin
			row_sel <= 0;
			col <= 0;
			px_buff <= 0;
			prev_row_valid <= 0;
			prev_row_pixel_s0 <= 0;
			prev_row_pixel_s1 <= 0;
			prev_row_pixel_left_s1 <= 0;
			px_buff_s1 <= 0;
			col_s0 <= 0;
			first_col_s0 <= 0;
			prev_row_valid_s0 <= 0;
			col_s1 <= 0;
			first_col_s1 <= 0;
			prev_row_valid_s1 <= 0;
			A_left <= 0;
			B_top <= 0;
			C_topleft <= 0;
			X_cur <= 0;
			nb_valid <= 0;
		end
		else begin
			nb_valid <= 0;
			if(px_valid) begin
				if(row_sel == 0)
					line_buff_cur[col] <= px_in;
				else
					line_buff[col] <= px_in;
				if(row_sel == 0)
					prev_row_pixel_s0 <= line_buff[col];
				else
					prev_row_pixel_s0 <= line_buff_cur[col];
				col_s0 <= col;
				first_col_s0 <= (col == 0);
				prev_row_valid_s0 <= prev_row_valid;
				X_cur <= px_in;
				if(col == W-1) begin
					col <= 0;
					row_sel <= ~row_sel;
					prev_row_valid <= 1;
				end
				else begin
					col <= col + 1;
				end
				px_buff <= px_in;
				prev_row_pixel_s1 <= prev_row_pixel_s0;
				prev_row_pixel_left_s1 <= prev_row_pixel_s1;
				px_buff_s1 <= px_buff;
				col_s1 <= col_s0;
				first_col_s1 <= first_col_s0;
				prev_row_valid_s1 <= prev_row_valid_s0;
				if(!prev_row_valid_s1) begin
					A_left <= (col_s1 == 0) ? 0 : px_buff_s1;
					B_top <= 0;
					C_topleft <= 0;
					nb_valid <= 1;
				end
				else begin
					if(first_col_s1) begin
						A_left <= 0;
						B_top <= prev_row_pixel_s1;
						C_topleft <= 0;
						nb_valid <= 1;
					end
					else begin
						A_left <= px_buff_s1;
						B_top <= prev_row_pixel_s1;
						C_topleft <= prev_row_pixel_left_s1;
						nb_valid <= 1;
					end
				end
			end
		end
	end
endmodule
