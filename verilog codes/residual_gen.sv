module residual_gen #(parameter int BPP = 8, ERR_W = BPP+1)(
	input  logic                 	  pred_valid,
	input  logic [BPP-1:0]       	  X,
	input  logic [BPP-1:0]       	  X_hat,
	output logic                 	  err_valid,
	output logic signed [ERR_W-1:0] E
);
	always_comb begin
		if(pred_valid) begin
			E = $signed({1'b0,X}) - $signed({1'b0,X_hat});
			err_valid = 1;
		end
		else begin
			E = 0;
			err_valid = 0;
		end
	end
endmodule