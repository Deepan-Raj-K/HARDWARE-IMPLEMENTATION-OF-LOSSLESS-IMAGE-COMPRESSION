`timescale 1ns/1ps

module med_rice_tb;

    parameter BPP = 8;
    parameter W   = 4;
    parameter H   = 4;
    parameter TOTAL_PIXELS = W * H;

    // -------------------------------------------------
    // Clock & Reset
    // -------------------------------------------------

    logic clk;
    logic rst_n;

    // -------------------------------------------------
    // DUT inputs
    // -------------------------------------------------

    logic in_valid;
    logic [BPP-1:0] in_pixel;
    logic frame_start;
    logic frame_end;

    // -------------------------------------------------
    // DUT outputs
    // -------------------------------------------------

    logic wr_en;
    logic [31:0] wr_addr;
    logic [7:0]  wr_data;

    // -------------------------------------------------
    // Statistics
    // -------------------------------------------------

    integer byte_count;
    real compression_ratio;
    real bits_per_pixel;
    real compression_percent;
    real throughput_MBps;
    real time_sec;

    time start_time;
    time end_time;

    // -------------------------------------------------
    // Image memory
    // -------------------------------------------------

    logic [BPP-1:0] image_mem [0:TOTAL_PIXELS-1];

    integer outfile;

    // -------------------------------------------------
    // DUT
    // -------------------------------------------------

    med_rice #(
        .BPP(BPP),
        .W(W)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .in_pixel(in_pixel),
        .frame_start(frame_start),
        .frame_end(frame_end),
        .wr_en(wr_en),
        .wr_addr(wr_addr),
        .wr_data(wr_data)
    );

    // -------------------------------------------------
    // Clock
    // -------------------------------------------------

    always #5 clk = ~clk;

    // -------------------------------------------------
    // Output writer + byte counter
    // -------------------------------------------------

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            byte_count <= 0;
        end
        else if (wr_en) begin
            $fwrite(outfile,"%c",wr_data);
            byte_count <= byte_count + 1;
        end
    end



    // -------------------------------------------------
    // Main Test
    // -------------------------------------------------

    initial begin

        clk = 0;
        rst_n = 0;

        in_valid = 0;
        frame_start = 0;
        frame_end = 0;

        // Load image
        $display("Loading image...");
        $readmemh("C:/Users/wwwde/Documents/Academics/mini project/pre and post processing/demo.hex", image_mem);

        // Open output file
        outfile = $fopen("C:/Users/wwwde/Documents/Academics/mini project/pre and post processing/compressed_demo1.bin", "wb");

        if(outfile == 0) begin
            $display("ERROR: cannot open output file");
            $finish;
        end

        #50;
        rst_n = 1;

        #20;

        start_time = $time;

        // -------------------------------------------------
        // Frame start
        // -------------------------------------------------

        frame_start = 1;
        @(posedge clk);
        frame_start = 0;

        // -------------------------------------------------
        // Send pixels
        // -------------------------------------------------

        for(int i = 0; i < TOTAL_PIXELS; i++) begin
            @(posedge clk);
            in_valid = 1;
            in_pixel = image_mem[i];
        end

        @(posedge clk);
        in_valid = 0;

        // -------------------------------------------------
        // Frame end
        // -------------------------------------------------

        frame_end = 1;
        @(posedge clk);
        frame_end = 0;

        // Wait for encoder pipeline to finish
        wait(dut.enc_busy == 0);
			repeat(20) @(posedge clk);

        end_time = $time;

        // -------------------------------------------------
        // Compute statistics
        // -------------------------------------------------

        compression_ratio   = (TOTAL_PIXELS*BPP/8.0) / byte_count;
        bits_per_pixel      = (byte_count * 8.0) / TOTAL_PIXELS;
        compression_percent = (1.0 - (byte_count / (TOTAL_PIXELS*BPP/8.0))) * 100.0;

        time_sec = (end_time - start_time) * 1e-9;

        throughput_MBps = (TOTAL_PIXELS / (1024.0*1024.0)) / time_sec;

        // -------------------------------------------------
        // Print results
        // -------------------------------------------------

        $display("=================================");
        $display("Compression Completed Successfully");
        $display("Original Size (bytes)  : %0d", TOTAL_PIXELS*BPP/8);
        $display("Compressed Bytes       : %0d", byte_count);
        $display("Compression Ratio      : %0f", compression_ratio);
        $display("Bits Per Pixel (bpp)   : %0f", bits_per_pixel);
        $display("Compression Reduction  : %0f %%", compression_percent);
        $display("Encoding Time (ns)     : %0t", end_time - start_time);
        $display("Throughput (MB/s)      : %0f", throughput_MBps);
        $display("=================================");

        $fclose(outfile);

        $finish;

    end

endmodule