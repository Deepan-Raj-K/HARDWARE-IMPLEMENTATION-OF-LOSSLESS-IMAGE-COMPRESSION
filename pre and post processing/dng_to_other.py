import os
from pathlib import Path

import rawpy
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

# Enable HEIC/HEIF support in Pillow
register_heif_opener()

# ====== SET YOUR FOLDER PATH HERE ======
folder_path = "dataset"   # change this

# Convert all .dng files in the folder
folder = Path(folder_path)
dng_files = list(folder.glob("*.dng")) + list(folder.glob("*.DNG"))

if not dng_files:
    print("No DNG files found in the folder.")
    raise SystemExit

def file_size_info(path):
    size_bytes = os.path.getsize(path)
    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024
    return f"{size_bytes} bytes | {size_kb:.2f} KB | {size_mb:.2f} MB"

for dng_file in dng_files:
    try:
        print(f"\nProcessing: {dng_file.name}")

        # Read DNG using rawpy
        with rawpy.imread(str(dng_file)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=8
            )

        # Convert numpy array to PIL image
        rgb_img = Image.fromarray(rgb)

        # Convert to grayscale
        gray_img = rgb_img.convert("L")

        # Output file names in the same folder
        base_name = dng_file.stem
        png_path  = dng_file.with_name(base_name + "_gray.png")
        jpg_path  = dng_file.with_name(base_name + "_gray.jpg")
        heic_path = dng_file.with_name(base_name + "_gray.heic")

        # Save grayscale PNG
        gray_img.save(png_path, format="PNG")

        # Save grayscale JPEG
        gray_img.save(jpg_path, format="JPEG", quality=90)

        # Save grayscale HEIC
        gray_img.save(heic_path, format="HEIF", quality=90)

        # Print sizes
        print(f"Created: {png_path.name}  -> {file_size_info(png_path)}")
        print(f"Created: {jpg_path.name}  -> {file_size_info(jpg_path)}")
        print(f"Created: {heic_path.name} -> {file_size_info(heic_path)}")

    except Exception as e:
        print(f"Error processing {dng_file.name}: {e}")