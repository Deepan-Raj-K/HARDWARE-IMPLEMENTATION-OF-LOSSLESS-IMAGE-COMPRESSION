# MEDRICE — Hardware Implementation of Lossless Image Compression

FPGA-based lossless image compression using **MED (Median Edge Detector)** prediction combined with **Rice (Golomb-Rice)** entropy coding.

## Overview

Implements a complete lossless compression pipeline: input pixel data → MED prediction → Rice/escape encoding → bit-stream output, and the corresponding decoder. Designed in Verilog RTL for Quartus Prime on Cyclone V FPGA.

## Repository Structure

```
├── rtl/
│   ├── encoder/
│   │   ├── medrice_escape_encoder.v   # Top-level encoder (MED + Rice + escape)
│   │   ├── tb_encoder.v               # Encoder testbench
│   │   ├── medrice_escape.qpf         # Quartus project (encoder)
│   │   └── serv_req_info.txt          # Pin/service request info
│   │
│   └── decoder/
│       ├── medrice_escape_decode.v    # Top-level decoder with escape support
│       ├── medrice_decoder.v          # MED + Rice decoder core
│       ├── bit_unpacker.v             # Bit-stream unpacker
│       ├── decoder_tb.v               # Decoder testbench
│       └── medrice_decode.qpf         # Quartus project (decoder)
│
├── scripts/                # Python pre/post-processing & reference
│   ├── encoder.py              # Python encoder reference
│   ├── escape_coding.py        # Escape coding module
│   ├── escape_decoding.py      # Escape decoding module
│   ├── bmp_to_hex.py           # BMP → hex conversion
│   ├── dng_to_hex.py           # DNG/RAW → hex conversion
│   ├── format_changer.py       # Image format conversion
│   ├── img_to_hex.m            # MATLAB image → hex
│   └── ... (additional utility scripts)
│
├── data/
│   ├── test_images/         # DNG test images & dataset sheet
│   ├── misc/                # Image variants (bin/hex/tiff)
│   └── compressed_output.bin
│
├── docs/
│   ├── Report.pdf           # Project report
│   └── Report.docx
│
├── sim/                     # ModelSim do-files
│   ├── medrice_escape_run_msim_rtl_verilog.do
│   └── medrice_decode_run_msim_rtl_verilog.do
│
└── .gitattributes           # Git LFS config for hex files
```

## Encoder Pipeline

1. **MED Prediction** — Predicts current pixel from 3 neighbours (W, NW, N)
2. **Rice Coding** — Encodes prediction residual using Golomb-Rice with adaptive k
3. **Escape Coding** — Handles large residuals via 12-bit literal fallback
4. **Bit Packing** — Serializes codewords into output bit-stream

## Simulation

```bash
# Encoder
vlog -quiet -work work rtl/encoder/medrice_escape_encoder.v rtl/encoder/tb_encoder.v
vsim -c -voptargs="+acc" work.tb_encoder -do "sim/medrice_escape_run_msim_rtl_verilog.do"

# Decoder
vlog -quiet -work work rtl/decoder/*.v
vsim -c -voptargs="+acc" work.decoder_tb -do "sim/medrice_decode_run_msim_rtl_verilog.do"
```

## Python Reference

```bash
python scripts/encoder.py          # Encoder reference
python scripts/escape_coding.py    # Escape coding module
python scripts/escape_decoding.py  # Escape decoding
```
