import rawpy
import numpy as np
from PIL import Image
import pillow_heif
from tkinter import Tk, filedialog
import os

# Enable HEIC support
pillow_heif.register_heif_opener()

# Hide tkinter root window
root = Tk()
root.withdraw()

# Open file selection dialog
file_path = filedialog.askopenfilename(
    title="Select a DNG Image",
    filetypes=[("DNG files", "*.dng")]
)

if not file_path:
    print("No file selected.")
    exit()

# Extract filename and directory
output_dir = os.path.dirname(file_path)

print("Reading DNG file...")

# Read DNG using rawpy
with rawpy.imread(file_path) as raw:
    rgb = raw.postprocess(
        use_camera_wb=True,
        no_auto_bright=True,
        output_bps=8
    )

print("Converting to grayscale...")

# Convert RGB → Grayscale
gray = np.dot(rgb[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)

# Convert numpy array to PIL image
gray_img = Image.fromarray(gray)

# -------- Save PNG --------
png_path = os.path.join(output_dir, "original_png.png")
gray_img.save(png_path)

# -------- Save JPEG --------
jpeg_path = os.path.join(output_dir, "original_jpg.jpg")
gray_img.save(jpeg_path, quality=95)

# -------- Save HEIC --------
heic_path = os.path.join(output_dir, "original_heic.heic")
gray_img.save(heic_path, format="HEIF", quality=90)

# -------- Save TIFF --------
tiff_path = os.path.join(output_dir, "original_tiff.tiff")
gray_img.save(tiff_path)

# -------- Save BMP --------
bmp_path = os.path.join(output_dir, "original_bmp.bmp")
gray_img.save(bmp_path)

print("\nConversion complete.")
print("Files saved:")

print("PNG :", png_path)
print("JPEG:", jpeg_path)
print("HEIC:", heic_path)
print("TIFF:", tiff_path)
print("BMP :", bmp_path)