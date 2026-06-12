import numpy as np
import os, io, math
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import rawpy
import matplotlib.pyplot as plt

# ---------------- CONFIGURATION ----------------
NOISE_THRESHOLD = 4  # Set to 0 for mathematically perfect (larger files)

def get_nearest_pow2_bits(max_val):
    """Finds the bit-depth tier: 1, 2, 4, 8, or 16."""
    if max_val == 0: return 1
    actual_bits = int(math.ceil(math.log2(max_val + 1)))
    for tier in [1, 2, 4, 8, 16]:
        if actual_bits <= tier:
            return tier
    return 16

def select_image():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title="Select RAW DNG", filetypes=[("DNG Files", "*.dng")])
    root.destroy()
    return path

def run_pipeline(path):
    # 1. DEVELOP RAW
    print("Step 1: Developing RAW...")
    with rawpy.imread(path) as raw:
        original_rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=8)
    
    # 2. GENERATE JPEG BASE
    print("Step 2: Generating JPEG Base...")
    img_pil = Image.fromarray(original_rgb)
    jpeg_buf = io.BytesIO()
    img_pil.save(jpeg_buf, format="JPEG", quality=90, subsampling=0)
    jpeg_img = np.array(Image.open(io.BytesIO(jpeg_buf.getvalue())))
    
    # 3. CALCULATE SMART RESIDUAL (Shifted to 0-255)
    print("Step 3: Calculating Residual & Sparsity...")
    diff = original_rgb.astype(np.int16) - jpeg_img.astype(np.int16)
    
    # Apply Sparsity Feature (Thresholding)
    diff[np.abs(diff) <= NOISE_THRESHOLD] = 0
    sparsity = (np.count_nonzero(diff == 0) / diff.size) * 100
    
    # Map to 0-255 range (128 is neutral)
    residual_unsigned = np.clip(diff + 128, 0, 255).astype(np.uint8)

    # 4. POWER OF 2 BIT-DEPTH LOGIC
    max_val = np.max(residual_unsigned)
    target_bits = get_nearest_pow2_bits(max_val)
    
    # 5. SAVE ACTUAL FILES
    print("Step 4: Saving files...")
    base_name = os.path.splitext(os.path.basename(path))[0]
    
    # Save Original Reference
    Image.fromarray(original_rgb).save(f"{base_name}_ref.png")
    
    # Save JPEG Base
    with open(f"{base_name}_base.jpg", "wb") as f:
        f.write(jpeg_buf.getvalue())
        
    # Save Residual PNG (Using the logic of your requested bit-depth)
    res_path = f"{base_name}_residual_{target_bits}bit.png"
    Image.fromarray(residual_unsigned).save(res_path, compress_level=9)

    # 6. CALCULATE FINAL STATS
    orig_kb = os.path.getsize(f"{base_name}_ref.png") / 1024
    jpeg_kb = len(jpeg_buf.getvalue()) / 1024
    res_kb = os.path.getsize(res_path) / 1024
    hybrid_total = jpeg_kb + res_kb
    
    stats = (f"Max Residual: {max_val}\n"
             f"Stored Bit-Depth: {target_bits}-bit\n"
             f"Sparsity: {sparsity:.1f}% zeros\n\n"
             f"Original PNG: {orig_kb:.2f} KB\n"
             f"Hybrid Total: {hybrid_total:.2f} KB\n"
             f"Savings: {(1 - hybrid_total/orig_kb)*100:.1f}%")
    
    print("\n" + stats)

    # 7. DISPLAY EVERYTHING
    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    axes[0].imshow(original_rgb)
    axes[0].set_title(f"Original\n{orig_kb:.0f} KB")
    
    axes[1].imshow(jpeg_img)
    axes[1].set_title(f"JPEG Base\n{jpeg_kb:.0f} KB")
    
    axes[2].imshow(residual_unsigned)
    axes[2].set_title(f"Residual ({target_bits}-bit)\n{res_kb:.0f} KB")
    
    for ax in axes: ax.axis('off')
    plt.suptitle(f"Hybrid Compression Results for {base_name}")
    plt.show()

if __name__ == "__main__":
    file_path = select_image()
    if file_path:
        run_pipeline(file_path)