module med_predictor #(parameter int BPP = 8)(
    input  logic           nb_valid,
    input  logic [BPP-1:0] A,
    input  logic [BPP-1:0] B,
    input  logic [BPP-1:0] C,
    output logic           pred_valid,
    output logic [BPP-1:0] X_hat
);
	logic [BPP-1:0] min;
	logic [BPP-1:0] max;
	logic signed [BPP:0] of;
	always_comb begin
		if(nb_valid) begin
			pred_valid = 1;
			min = (A<B)?A:B;
			max = (A>B)?A:B;
			if(C >= max) begin
				X_hat = min;
				of = 0;
			end
			else if(C <= min) begin
				X_hat = max;
				of = 0;
			end
			else begin
				of = $signed({1'b0,A}) + $signed({1'b0,B}) - $signed({1'b0,C});
				if(of > $signed({1'b0,{BPP{1'b1}}}))
					X_hat = {BPP{1'b1}};
				else if(of < 0)
					X_hat = 0;
				else
					X_hat = of[BPP-1:0];
			end
		end
		else begin
			of = 0;
			pred_valid = 0;
			min = 0;
			max = 0;
			X_hat = 0;
		end
	end
endmodule