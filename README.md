# MEDRICE — Hardware Implementation of Lossless Image Compression

FPGA-based lossless image compression using **MED (Median Edge Detector)** prediction combined with **Rice (Golomb-Rice)** entropy coding.

## Overview

Implements a complete lossless compression pipeline: input pixel data → MED prediction → Rice/escape encoding → bit-stream output, and the corresponding decoder. Designed in Verilog RTL targeting both Intel Cyclone V (Quartus) and Xilinx Zynq-7020 (Vivado).

## Repository Structure

```
├── rtl/
│   ├── encoder/
│   │   ├── medrice_escape_encoder.v   # Top-level encoder (MED + Rice + escape)
│   │   ├── tb_encoder.v               # Encoder testbench
│   │   ├── medrice_escape.qpf         # Quartus project (encoder)
│   │   └── medrice_escape.qsf         # Quartus settings (encoder)
│   │
│   └── decoder/
│       ├── medrice_escape_decode.v    # Top-level decoder with escape support
│       ├── medrice_decoder.v          # MED + Rice decoder core
│       ├── bit_unpacker.v             # Bit-stream unpacker
│       ├── decoder_tb.v               # Decoder testbench
│       └── medrice_decode.qpf         # Quartus project (decoder)
│
├── vivado/
│   ├── Locoi.xpr                  # Vivado project (Zynq-7020)
│   └── power_power_1.txt          # Vivado power report (28.4W)
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
├── sim/                     # ModelSim do-files
│   ├── medrice_escape_run_msim_rtl_verilog.do
│   └── medrice_decode_run_msim_rtl_verilog.do
│
├── data/
│   ├── test_images/         # DNG test images & dataset sheet
│   ├── misc/                # Compressed/test image variants
│   └── compressed_output.bin
│
├── docs/
│   ├── Report.pdf           # Project report
│   └── Report.docx
│
├── .gitattributes           # Git LFS config for hex files
└── .gitignore
```

## Encoder Pipeline

1. **MED Prediction** — Predicts current pixel from 3 neighbours (W, NW, N)
2. **Rice Coding** — Encodes prediction residual using Golomb-Rice with adaptive k
3. **Escape Coding** — Handles large residuals via 12-bit literal fallback
4. **Bit Packing** — Serializes codewords into output bit-stream

## FPGA Implementations

### Quartus (Intel Cyclone V)
Primary implementation targeting the Cyclone V `5CGXFC7C7F23C8` using Quartus Prime 20.1.  
RTL sources in `rtl/encoder/` and `rtl/decoder/`.

### Vivado (Xilinx Zynq-7020)
Secondary implementation targeting the Zynq-7020 `xc7z020clg400-1` using Vivado.  
Project file: `vivado/Locoi.xpr`  
Power report: `vivado/power_power_1.txt` (28.4W total on-chip power)

## Simulation

```bash
# Encoder (ModelSim)
vlog -quiet -work work rtl/encoder/medrice_escape_encoder.v rtl/encoder/tb_encoder.v
vsim -c -voptargs="+acc" work.tb_encoder -do "sim/medrice_escape_run_msim_rtl_verilog.do"

# Decoder (ModelSim)
vlog -quiet -work work rtl/decoder/*.v
vsim -c -voptargs="+acc" work.decoder_tb -do "sim/medrice_decode_run_msim_rtl_verilog.do"
```

## Python Reference

```bash
python scripts/escape_coding.py    # Full encode/decode with escape support
python scripts/encoder.py          # Basic encoder reference
python scripts/escape_decoding.py  # Standalone decoder
```
