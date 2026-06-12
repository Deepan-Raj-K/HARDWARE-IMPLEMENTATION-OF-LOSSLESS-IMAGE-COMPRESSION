import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import io
import rawpy
import subprocess
import sys
from datetime import datetime

# ============================================================================
# FILE SELECTION
# ============================================================================

def select_image():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select DNG Raw Image",
        filetypes=[("DNG Files", "*.dng"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path

# ============================================================================
# IMAGE PROCESSING
# ============================================================================

def load_dng_raw(path):
    print("Processing DNG file...")
    with rawpy.imread(path) as raw:
        # Postprocess converts raw sensor data to RGB
        rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True, bright=1.0)
    return rgb

def calculate_optimized_bits(residual_abs):
    """Calculates the minimum n bits needed to store the max residual value."""
    max_val = np.max(residual_abs)
    if max_val == 0:
        return 0
    # Find n such that 2^n > max_val
    n = int(np.ceil(np.log2(max_val + 1)))
    return n

# ============================================================================
# MAIN LOGIC
# ============================================================================

def run_hybrid_logic(image_path):
    if not image_path:
        return

    # 1. LOAD RAW DATA
    original_arr = load_dng_raw(image_path)
    original_arr = np.clip(original_arr, 0, 255).astype(np.uint8)
    
    # 2. GENERATE JPEG PREDICTOR (Compressed)
    buffer = io.BytesIO()
    Image.fromarray(original_arr).save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    jpeg_arr = np.array(Image.open(buffer))

    # 3. CALCULATE RESIDUAL
    # We use int16 to handle negative differences before taking absolute value
    raw_residual = original_arr.astype(np.int16) - jpeg_arr.astype(np.int16)
    residual_abs = np.abs(raw_residual).astype(np.uint8)
    
    # Calculate required bit-depth n
    n_bits = calculate_optimized_bits(residual_abs)
    
    # For visualization, we boost the residual
    residual_view = np.clip(residual_abs.astype(np.float32) * 10, 0, 255).astype(np.uint8)

    # 4. RECONSTRUCT (LOSSLESS)
    reconstructed_arr = np.clip(jpeg_arr.astype(np.int16) + raw_residual, 0, 255).astype(np.uint8)
    
    # Verify Reconstruction
    mse = np.mean((original_arr.astype(np.float32) - reconstructed_arr.astype(np.float32))**2)

    # 5. DISPLAY RESULTS
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(f"Hybrid Compression Analysis\nResidual Max Bit-Depth ($n$): {n_bits} bits", fontsize=14)

    axes[0, 0].imshow(original_arr)
    axes[0, 0].set_title("Original (Raw RGB)")
    
    axes[0, 1].imshow(jpeg_arr)
    axes[0, 1].set_title("JPEG Predictor (Q=90)")
    
    axes[1, 0].imshow(residual_view, cmap='inferno')
    axes[1, 0].set_title(f"Residual Map (Boosted x10)\nStored in {n_bits}-bit space")
    
    axes[1, 1].imshow(reconstructed_arr)
    axes[1, 1].set_title(f"Lossless Reconstruction\nMSE: {mse:.4f}")

    for ax in axes.flatten():
        ax.axis('off')

    plt.tight_layout()
    plt.show()

    # 6. SAVE FILES
    save_files(original_arr, jpeg_arr, residual_abs, reconstructed_arr, n_bits)

def save_files(orig, jpg, res, recon, n):
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Select Save Folder")
    if not folder:
        return

    ts = datetime.now().strftime("%H%M%S")
    
    # Saving
    Image.fromarray(orig).save(os.path.join(folder, f"original_{ts}.png"))
    Image.fromarray(jpg).save(os.path.join(folder, f"jpeg_base_{ts}.jpg"), quality=90)
    Image.fromarray(res).save(os.path.join(folder, f"residual_{n}bit_{ts}.png"))
    Image.fromarray(recon).save(os.path.join(folder, f"reconstructed_{ts}.png"))

    print(f"\n--- Processing Complete ---")
    print(f"Max Residual Value: {np.max(res)}")
    print(f"Required Bit-Depth (n): {n} bits")
    print(f"Lossless Reconstruction MSE: {np.mean((orig.astype(np.float32)-recon.astype(np.float32))**2)}")
    
    messagebox.showinfo("Done", f"Files saved.\nResidual requires {n} bits per pixel.")
    root.destroy()

if __name__ == "__main__":
    path = select_image()
    if path:
        run_hybrid_logic(path)