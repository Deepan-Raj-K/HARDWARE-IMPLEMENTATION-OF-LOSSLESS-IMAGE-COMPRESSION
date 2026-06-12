`timescale 1ns/1ps
module decoder_tb;

    parameter WIDTH  = 3072;
    parameter HEIGHT = 4080;

    reg clk, rst;
    reg [7:0] byte_in;
    reg valid_in;

    wire [7:0] pixel_out;
    wire valid_out;

    integer infile, outfile;
    integer r;
    integer count;

    medrice_escape_decode uut (
        .clk(clk),
        .rst(rst),
        .byte_in(byte_in),
        .valid_in(valid_in),
        .pixel_out(pixel_out),
        .valid_out(valid_out)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst = 1;
        valid_in = 0;
        count = 0;

        #20 rst = 0;

        infile = $fopen("C:/Users/wwwde/Documents/Academics/mini project/escape_coding/compressed_output.bin", "rb");
        outfile = $fopen("C:/Users/wwwde/Documents/Academics/mini project/escape_decoding/decoded.hex", "w");

        while (!$feof(infile)) begin
            @(posedge clk);
            r = $fread(byte_in, infile);
            valid_in = 1;
        end

        valid_in = 0;

        #10000;
        $finish;
    end

    always @(posedge clk) begin
        if (valid_out) begin
            $fwrite(outfile, "%h\n", pixel_out);
            count = count + 1;
        end
    end

endmodule