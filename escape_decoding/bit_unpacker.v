module bit_unpacker (
    input        clk,
    input        rst,
    input  [7:0] byte_in,
    input        valid_in,
    output reg   bit_out,
    output reg   valid_out
);

    reg [7:0] buffer;
    reg [2:0] cnt;
    reg       active;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            buffer    <= 8'd0;
            cnt       <= 3'd0;
            active    <= 0;
            valid_out <= 0;
            bit_out   <= 0;
        end else begin
            valid_out <= 0;

            if (valid_in) begin
                buffer <= byte_in;
                cnt    <= 3'd7;
                active <= 1;
            end else if (active) begin
                bit_out   <= buffer[cnt];
                valid_out <= 1;

                if (cnt == 0)
                    active <= 0;
                else
                    cnt <= cnt - 1;
            end
        end
    end
endmodule