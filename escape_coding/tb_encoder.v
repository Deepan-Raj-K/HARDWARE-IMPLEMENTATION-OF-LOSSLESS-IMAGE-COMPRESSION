`timescale 1ns/1ps

module tb_encoder;

    parameter WIDTH  = 512;
    parameter HEIGHT = 512;
    parameter BPP    = 8;
    parameter TOTAL_PIXELS = WIDTH * HEIGHT;

    // ── Clock & reset ──────────────────────────────────────────────
    reg clk;
    reg rst;

    // ── DUT ports ─────────────────────────────────────────────────
    reg [7:0] pixel_in;
    reg       valid_in;
    reg       flush;

    wire [7:0] byte_out;
    wire       valid_out;
    wire       bit_out;
    wire       bit_valid;
    wire       ready;

    // ── File handles ──────────────────────────────────────────────
    integer infile, outfile;
    integer r, scan_status;

    // ── Image memory ──────────────────────────────────────────────
    reg [7:0] image_mem [0:TOTAL_PIXELS-1];

    // ── Stats ─────────────────────────────────────────────────────
    integer pixel_count;
    integer bit_count;
    integer byte_count;

    time start_time;
    time end_time;

    real original_bits;
    real compression_ratio;
    real bpp_out;

    // ── Control ───────────────────────────────────────────────────
    integer idx;
    reg     sending;

    // ── DUT ───────────────────────────────────────────────────────
    medrice_escape_encoder #(.IMG_WIDTH(WIDTH)) uut (
        .clk      (clk),
        .rst      (rst),
        .pixel_in (pixel_in),
        .valid_in (valid_in),
        .flush    (flush),
        .byte_out (byte_out),
        .valid_out(valid_out),
        .bit_out  (bit_out),
        .bit_valid(bit_valid),
        .ready    (ready)
    );

    // ── Clock ─────────────────────────────────────────────────────
    always #5 clk = ~clk;

    // ── Bit counter ───────────────────────────────────────────────
    always @(posedge clk) begin
        if (bit_valid)
            bit_count = bit_count + 1;
    end

    // ── Byte output ───────────────────────────────────────────────
    always @(posedge clk) begin
        if (valid_out) begin
            $fwrite(outfile, "%c", byte_out);
            byte_count = byte_count + 1;
        end
    end

    // ── Pixel feed logic (STRICT 1-cycle pulse) ───────────────────
    always @(posedge clk) begin
        if (!rst && sending) begin
            if (valid_in) begin
                valid_in <= 0;
            end 
            else if (ready && idx < TOTAL_PIXELS) begin
                pixel_in   <= image_mem[idx];
                valid_in   <= 1;
                idx        = idx + 1;
                pixel_count = pixel_count + 1;

                // Progress print
                if (idx % 5000 == 0)
                    $display("Progress: %0d / %0d", idx, TOTAL_PIXELS);
            end

            if (idx == TOTAL_PIXELS)
                sending <= 0;
        end
    end

    // ── Main control ──────────────────────────────────────────────
    initial begin
        clk         = 0;
        rst         = 1;
        valid_in    = 0;
        flush       = 0;
        pixel_in    = 0;
        sending     = 0;
        idx         = 0;

        pixel_count = 0;
        bit_count   = 0;
        byte_count  = 0;

        #20;
        rst = 0;

        // ── FILE LOAD (SAFE) ───────────────────────────────────────
        infile = $fopen("F:/Documents/Academics/mini project/pre and post processing/misc/top10/img12.hex", "r");
        if (infile == 0) begin
            $display("ERROR: Cannot open img.hex");
            $finish;
        end

        for (r = 0; r < TOTAL_PIXELS; r = r + 1) begin
            if ($feof(infile)) begin
                $display("ERROR: EOF reached early at pixel %0d", r);
                $finish;
            end

            scan_status = $fscanf(infile, "%h\n", image_mem[r]);

            if (scan_status != 1) begin
                $display("ERROR: fscanf failed at pixel %0d", r);
                $finish;
            end
        end

        $fclose(infile);
        $display("Image loaded successfully!");

        // ── OUTPUT FILE ────────────────────────────────────────────
        outfile = $fopen("F:/Documents/Academics/mini project/pre and post processing/misc/top10/img12.bin", "wb");

        $display("=====================================");
        $display("MEDRICE Compression Simulation Start");
        $display("=====================================");

        start_time = $time;

        sending = 1;

        // ── Wait until all pixels sent ─────────────────────────────
        wait (sending == 0);

        $display("All pixels sent. Waiting for pipeline...");

        // ── Drain pipeline ─────────────────────────────────────────
        repeat (50) @(posedge clk);

        // ── Flush remaining bits ───────────────────────────────────
        @(posedge clk); flush <= 1;
        @(posedge clk); flush <= 1;
        @(posedge clk); flush <= 0;

        repeat (20) @(posedge clk);

        end_time = $time;

        $fclose(outfile);

        // ── Results ───────────────────────────────────────────────
        original_bits     = pixel_count * BPP;
        compression_ratio = original_bits / bit_count;
        bpp_out           = bit_count * 1.0 / pixel_count;

        $display("\nCompression Results");
        $display("---------------------");
        $display("Pixels Processed : %0d", pixel_count);
        $display("Original bits    : %0.0f", original_bits);
        $display("Compressed bits  : %0d", bit_count);
        $display("Compressed bytes : %0d", byte_count);
        $display("Compression ratio: %0.4f", compression_ratio);
        $display("Bits per pixel   : %0.4f", bpp_out);

        $display("\nTiming");
        $display("---------------------");
        $display("Total time : %t ns", (end_time - start_time));

        $display("\n=====================================");
        $display("Simulation Completed!");
        $display("=====================================");

        $finish;
    end

endmodule