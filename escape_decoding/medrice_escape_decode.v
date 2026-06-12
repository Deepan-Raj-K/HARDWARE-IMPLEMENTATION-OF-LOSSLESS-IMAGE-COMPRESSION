module medrice_escape_decode (
    input        clk,
    input        rst,

    input  [7:0] byte_in,
    input        valid_in,

    output [7:0] pixel_out,
    output       valid_out
);

    wire bit, bit_valid;
    wire [7:0] A,B,C;

    bit_unpacker bu (
        .clk(clk), .rst(rst),
        .byte_in(byte_in), .valid_in(valid_in),
        .bit_out(bit), .valid_out(bit_valid)
    );

    line_buffer lb (
        .clk(clk), .rst(rst),
        .pixel_in(pixel_out),
        .valid_in(valid_out),
        .A(A), .B(B), .C(C)
    );

    medrice_decoder dec (
        .clk(clk), .rst(rst),
        .bit_in(bit), .bit_valid(bit_valid),
        .A(A), .B(B), .C(C),
        .pixel_out(pixel_out),
        .valid_out(valid_out),
        .ready()
    );

endmodule