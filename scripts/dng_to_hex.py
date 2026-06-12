import os
import rawpy
import numpy as np
import cv2

# ==========================
# USER INPUT
# ==========================
INPUT_FOLDER = "dataset"   # <-- change this

# ==========================
# FUNCTION: DNG → BMP + HEX
# ==========================
def dng_to_outputs(dng_path):
    try:
        # Read RAW image and convert to RGB
        with rawpy.imread(dng_path) as raw:
            rgb = raw.postprocess()

        # Convert RGB to grayscale
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

        # Prepare output file paths
        base_name = os.path.splitext(dng_path)[0]
        bmp_path = base_name + "_gray.bmp"
        hex_path = base_name + ".hex"

        # ==========================
        # SAVE GRAYSCALE BMP
        # ==========================
        cv2.imwrite(bmp_path, gray)

        # ==========================
        # SAVE HEX FILE
        # ==========================
        flat_pixels = gray.flatten()

        with open(hex_path, 'w') as f:
            for pixel in flat_pixels:
                f.write(f"{pixel:02X}\n")  # 2-digit hex per pixel

        print(f"✔ Done: {os.path.basename(dng_path)}")
        print(f"   → BMP: {os.path.basename(bmp_path)}")
        print(f"   → HEX: {os.path.basename(hex_path)}")

    except Exception as e:
        print(f"✘ Failed: {dng_path}")
        print(f"   Error: {e}")


# ==========================
# MAIN LOOP
# ==========================
def process_folder(folder):
    if not os.path.exists(folder):
        print("Folder not found!")
        return

    for file in os.listdir(folder):
        if file.lower().endswith(".dng"):
            full_path = os.path.join(folder, file)
            dng_to_outputs(full_path)


# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    process_folder(INPUT_FOLDER)