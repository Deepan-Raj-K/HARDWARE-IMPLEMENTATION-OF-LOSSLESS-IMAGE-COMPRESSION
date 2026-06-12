import os
import cv2
import numpy as np

# ==========================
# USER INPUT
# ==========================
INPUT_FOLDER = "F:\Documents\Academics\mini project\pre and post processing\misc\misc"   # <-- change this

# ==========================
# FUNCTION: BMP → HEX
# ==========================
def bmp_to_hex(bmp_path):
    try:
        # Read image (handles both grayscale and color)
        img = cv2.imread(bmp_path, cv2.IMREAD_UNCHANGED)

        if img is None:
            raise ValueError("Image not readable")

        # If image is color → convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img  # already grayscale

        # Prepare output path
        base_name = os.path.splitext(bmp_path)[0]
        hex_path = base_name + ".hex"

        # Flatten pixels
        flat_pixels = gray.flatten()

        # Write HEX file
        with open(hex_path, 'w') as f:
            for pixel in flat_pixels:
                f.write(f"{int(pixel):02X}\n")

        print(f"✔ Converted: {os.path.basename(bmp_path)} → {os.path.basename(hex_path)}")

    except Exception as e:
        print(f"✘ Failed: {bmp_path}")
        print(f"   Error: {e}")


# ==========================
# MAIN LOOP
# ==========================
def process_folder(folder):
    if not os.path.exists(folder):
        print("Folder not found!")
        return

    for file in os.listdir(folder):
        if file.lower().endswith(".tiff"):
            full_path = os.path.join(folder, file)
            bmp_to_hex(full_path)


# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    process_folder(INPUT_FOLDER)