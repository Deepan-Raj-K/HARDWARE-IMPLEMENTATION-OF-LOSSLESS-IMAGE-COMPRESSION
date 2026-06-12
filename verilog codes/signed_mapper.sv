module signed_mapper #(parameter int BPP = 8, U_W = BPP+1, ERR_W = BPP+1)(
	input  logic                    err_valid,
	input  logic signed [ERR_W-1:0] E,
	output logic                    map_valid,
	output logic [U_W-1:0]          U
);
	always_comb begin
		if(err_valid) begin
			U = (E << 1) ^ (E >> BPP);
			map_valid = 1;
		end
		else begin
			U = 0;
			map_valid = 0;
		end
	end
endmodule