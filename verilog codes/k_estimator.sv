module k_estimator #(
    parameter int BPP = 8,
    parameter int U_W = BPP+1,
    parameter int K_W = $clog2(U_W+1),
    parameter int S   = 4
)(
    input  logic            clk,
    input  logic            rst_n,
    input  logic            map_valid,
    input  logic [U_W-1:0]  U,

    output logic            k_valid,
    output logic [K_W-1:0]  k_param
);

    logic [U_W:0] A;
    logic [U_W:0] A_next;

    function automatic [K_W-1:0] msb_pos(input logic [U_W:0] value);
        int i;
        begin
            msb_pos = 0;
            for (i = U_W; i >= 0; i--) begin
                if (value[i]) begin
                    msb_pos = i[K_W-1:0];
                    break;
                end
            end
        end
    endfunction


    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            A <= 1;
            k_param <= 0;
            k_valid <= 0;
        end
        else begin

            k_valid <= 0;

            if (map_valid) begin

                // compute k from CURRENT A
                k_param <= msb_pos(A);
                k_valid <= 1;

                // update A
                A_next = A + ((U > A) ? ((U - A) >> S) : -((A - U) >> S));

                if (A_next < 1)
                    A <= 1;
                else
                    A <= A_next;

            end

        end
    end

endmodule