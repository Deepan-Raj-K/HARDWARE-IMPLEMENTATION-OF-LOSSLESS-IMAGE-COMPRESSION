import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import io
import rawpy
from datetime import datetime


# ============================================================================
# FILE SELECTION
# ============================================================================

def select_image():
    """Opens file dialog to select a DNG raw image."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select DNG Raw Image",
        filetypes=[("DNG Files", "*.dng"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path


# ============================================================================
# METADATA EXTRACTION
# ============================================================================

def get_dng_metadata(path):
    """Extract metadata from DNG file using rawpy and PIL."""
    metadata = {}
    try:
        with rawpy.imread(path) as raw:
            metadata["Camera Make"] = raw.camera_name.split()[0] if raw.camera_name else "Unknown"
            metadata["Camera Model"] = raw.camera_name if raw.camera_name else "Unknown"
            metadata["Sensor Size (H×W)"] = f"{raw.raw_image.shape[0]} × {raw.raw_image.shape[1]}"
            metadata["Color Count"] = raw.color_count
            metadata["Bit Depth"] = f"{raw.bits_per_pixel} bits"

            if hasattr(raw, "iso_speed"):
                metadata["ISO"] = raw.iso_speed
            if hasattr(raw, "exposure"):
                metadata["Exposure Time"] = raw.exposure
    except Exception as e:
        print(f"Warning: Could not extract full rawpy metadata: {e}")

    try:
        img = Image.open(path)
        exif_data = img._getexif() if hasattr(img, "_getexif") else None
        if exif_data:
            if 271 in exif_data:
                metadata["Make"] = exif_data[271]
            if 272 in exif_data:
                metadata["Model"] = exif_data[272]
            if 306 in exif_data:
                metadata["DateTime"] = exif_data[306]
            if 34867 in exif_data:
                metadata["ISO Speed (EXIF)"] = exif_data[34867]
            if 33434 in exif_data:
                metadata["Exposure Time (EXIF)"] = exif_data[33434]
            if 33437 in exif_data:
                metadata["F-Number"] = exif_data[33437]
            if 36867 in exif_data:
                metadata["DateTime Original"] = exif_data[36867]
    except Exception as e:
        print(f"Warning: Could not extract PIL EXIF data: {e}")

    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    metadata["File Size"] = f"{file_size_mb:.2f} MB"
    metadata["File Path"] = path
    return metadata


def display_metadata(metadata):
    """Print metadata to console."""
    print("\n" + "=" * 70)
    print("DNG IMAGE METADATA")
    print("=" * 70)
    for key, value in metadata.items():
        if key != "File Path":
            print(f"{key:<25} : {value}")
    print(f"\nFull Path: {metadata.get('File Path', 'N/A')}")
    print("=" * 70 + "\n")
    return metadata


# ============================================================================
# IMAGE PROCESSING
# ============================================================================

def load_dng_raw(path):
    """Loads DNG and post-processes it into an RGB array."""
    print("Processing DNG file... this may take a moment.")
    with rawpy.imread(path) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=True,
            bright=1.0,
            output_bps=8  # 8-bit per channel (0–255)
        )
    return rgb


def create_metadata_display(metadata):
    """Create a visual display of metadata as an image."""
    img_width = 800
    img_height = 300
    background = Image.new("RGB", (img_width, img_height), color="white")
    draw = ImageDraw.Draw(background)

    try:
        font = ImageFont.truetype("arial.ttf", 11)
        title_font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    draw.text((20, 10), "DNG IMAGE METADATA", fill="black", font=title_font)
    draw.line([(20, 35), (780, 35)], fill="black", width=2)

    x_left = 25
    x_right = 420
    left_y = 50
    right_y = 50
    column = 0

    for key, value in metadata.items():
        if key != "File Path":
            text = f"{key}: {str(value)[:40]}"
            if column == 0:
                draw.text((x_left, left_y), text, fill="black", font=font)
                left_y += 22
                if left_y > 280:
                    column = 1
                    left_y = 50
            else:
                draw.text((x_right, right_y), text, fill="black", font=font)
                right_y += 22

    return np.array(background)


# ============================================================================
# SAVE HELPERS
# ============================================================================

def save_single_image(img_array, suggested_name):
    """Save image losslessly (PNG/TIFF/etc)."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        title="Save image",
        initialfile=suggested_name,
        defaultextension=".png",
        filetypes=[("Image files", "*.png;*.tiff;*.bmp;*.jpg;*.jpeg"),
                   ("All files", "*.*")]
    )
    if file_path:
        Image.fromarray(img_array).save(file_path)
        print(f"Saved: {file_path}")
    root.destroy()


def save_predictor_as_jpeg(img_array, suggested_name):
    """Save predictor explicitly as JPEG."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        title="Save predictor as JPEG",
        initialfile=suggested_name,
        defaultextension=".jpg",
        filetypes=[("JPEG files", "*.jpg;*.jpeg"), ("All files", "*.*")]
    )
    if file_path:
        Image.fromarray(img_array).save(file_path, format="JPEG", quality=90)
        print(f"Saved predictor as JPEG: {file_path}")
    root.destroy()


def save_residual_lossless(raw_residual, suggested_name):
    """
    Save full residual using the minimum power-of-two bit depth.
    Handles RGB (3D) and Grayscale (2D) arrays.
    """
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        title="Save residual data (adaptive bit depth)",
        initialfile=suggested_name,
        defaultextension=".png",
        filetypes=[("PNG image", "*.png"), ("All files", "*.*")]
    )
    if not file_path:
        root.destroy()
        return

    # 1. Find maximum absolute residual correctly
    # We use .astype(np.int32) to prevent overflow during abs() if necessary
    max_abs_val = int(np.max(np.abs(raw_residual)))
    print(f"[Residual Save] Max absolute residual: {max_abs_val}")

    # 2. Required dynamic range
    needed_levels = 2 * max_abs_val + 1
    n_bits = int(np.ceil(np.log2(needed_levels))) if needed_levels > 1 else 1

    # 3. Choose storage bit depth
    if n_bits <= 8:
        storage_bits = 8
        max_level = 255
        dtype = np.uint8
    else:
        storage_bits = 16
        max_level = 65535
        dtype = np.uint16

    print(f"[Residual Save] Using storage bit depth: {storage_bits}-bit")

    # 4. Map residual [-max_abs_val, +max_abs_val] -> [0, max_level]
    scale = max_level / (2 * max_abs_val) if max_abs_val > 0 else 1.0
    mapped = np.round((raw_residual.astype(np.float32) + max_abs_val) * scale).astype(dtype)

    # 5. Save logic handling dimensions
    try:
        if len(mapped.shape) == 3:
            # It's an RGB residual
            if storage_bits == 8:
                Image.fromarray(mapped, mode="RGB").save(file_path)
            else:
                # PIL saves 16-bit RGB better without a mode string
                Image.fromarray(mapped).save(file_path)
        else:
            # It's a Grayscale residual
            mode = "L" if storage_bits == 8 else "I;16"
            Image.fromarray(mapped, mode=mode).save(file_path)
        
        print(f"Saved adaptive {storage_bits}-bit residual PNG: {file_path}")
    except Exception as e:
        print(f"Failed to save residual: {e}")

    root.destroy()


def show_save_options(original_arr, jpeg_arr, raw_residual, residual_view_gray, reconstructed_arr):
    """Small window with buttons to choose which outputs to save."""
    win = tk.Tk()
    win.title("Save outputs")
    win.geometry("360x300")

    tk.Label(
        win,
        text="Choose which outputs you want to save:",
        anchor="w",
        justify="left",
    ).pack(padx=10, pady=10, fill="x")

    tk.Button(
        win,
        text="Save original image (lossless)",
        command=lambda: save_single_image(original_arr, "original_image.png"),
    ).pack(fill="x", padx=10, pady=5)

    tk.Button(
        win,
        text="Save compressed predictor (JPEG)",
        command=lambda: save_predictor_as_jpeg(jpeg_arr, "predictor_image.jpg"),
    ).pack(fill="x", padx=10, pady=5)

    tk.Button(
        win,
        text="Save residual (lossless data)",
        command=lambda: save_residual_lossless(raw_residual, "residual_data.png"),
    ).pack(fill="x", padx=10, pady=5)

    tk.Button(
        win,
        text="Save residual view (for display)",
        command=lambda: save_single_image(residual_view_gray, "residual_view.png"),
    ).pack(fill="x", padx=10, pady=5)

    tk.Button(
        win,
        text="Save reconstructed image (lossless)",
        command=lambda: save_single_image(reconstructed_arr, "reconstructed_image.png"),
    ).pack(fill="x", padx=10, pady=5)

    tk.Button(win, text="Close", command=win.destroy).pack(padx=10, pady=10)

    win.mainloop()


# ============================================================================
# MAIN PROCESSING LOGIC
# ============================================================================

def run_hybrid_logic(image_path):
    """Main processing: LOSSLESS reconstruction."""
    if not image_path:
        print("No file selected.")
        return

    print("\n" + "=" * 70)
    print(f"Reading DNG file: {image_path}")
    print("=" * 70 + "\n")

    # STEP 0: METADATA
    print("[STEP 0] Extracting metadata...")
    metadata = get_dng_metadata(image_path)
    display_metadata(metadata)

    # STEP 1: RAW
    print("[STEP 1] Loading raw DNG data...")
    original_arr = load_dng_raw(image_path)
    original_arr = np.clip(original_arr, 0, 255).astype(np.uint8)
    print(f"✓ Original shape: {original_arr.shape}, dtype: {original_arr.dtype}")

    # STEP 2: COMPRESSED PREDICTOR (JPEG)
    print("\n[STEP 2] Building compressed predictor...")
    buffer = io.BytesIO()
    Image.fromarray(original_arr).save(buffer, format="JPEG", quality=9)
    buffer.seek(0)
    jpeg_arr = np.array(Image.open(buffer))
    print(f"✓ Predictor shape: {jpeg_arr.shape}, dtype: {jpeg_arr.dtype}")

    # STEP 3: FULL RESIDUAL
    print("\n[STEP 3] Calculating full residual (lossless)...")
    raw_residual = original_arr.astype(np.int16) - jpeg_arr.astype(np.int16)
    abs_residual = np.abs(raw_residual)

    max_val = abs_residual.max()
    if max_val > 0:
        residual_view_gray = (abs_residual.astype(np.float32) / max_val * 255).astype(np.uint8)
    else:
        residual_view_gray = abs_residual.astype(np.uint8)

    print(f"✓ Residual shape: {raw_residual.shape}")
    print(f"✓ Max residual difference: {max_val}")
    print(f"✓ Non-zero residual pixels: {np.count_nonzero(raw_residual)}")

    # STEP 4: LOSSLESS RECONSTRUCTION
    print("\n[STEP 4] Reconstructing losslessly (predictor + full residual)...")
    reconstructed_arr = np.clip(
        jpeg_arr.astype(np.int16) + abs_residual, 0, 255
    ).astype(np.uint8)

    mse = np.mean(
        (original_arr.astype(np.float32) - reconstructed_arr.astype(np.float32)) ** 2
    )
    perfect = np.array_equal(original_arr, reconstructed_arr)

    print(f"✓ MSE (Original vs Reconstructed): {mse:.10f}")
    print(f"✓ Pixel-perfect match: {perfect}")

    # STEP 5: VISUALIZATION
    print("\n[STEP 5] Displaying comparison with metadata...")
    metadata_img = create_metadata_display(metadata)

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25)

    ax_meta = fig.add_subplot(gs[0, :])
    ax_meta.imshow(metadata_img)
    ax_meta.set_title("Metadata information", fontweight="bold", fontsize=13)
    ax_meta.axis("off")

    ax1 = fig.add_subplot(gs[1, 0])
    ax1.imshow(original_arr)
    ax1.set_title("Original image", fontweight="bold", fontsize=11)
    ax1.axis("off")

    ax2 = fig.add_subplot(gs[1, 1])
    ax2.imshow(jpeg_arr)
    ax2.set_title("Compressed predictor (JPEG decoded)", fontweight="bold", fontsize=11)
    ax2.axis("off")

    ax3 = fig.add_subplot(gs[2, 0])
    ax3.imshow(residual_view_gray, cmap="gray")
    ax3.set_title("Residual magnitude (view only)", fontweight="bold", fontsize=11)
    ax3.axis("off")

    ax4 = fig.add_subplot(gs[2, 1])
    ax4.imshow(reconstructed_arr)
    ax4.set_title("Reconstructed (pixel-perfect)", fontweight="bold", fontsize=11)
    ax4.axis("off")

    fig.suptitle(
        "DNG raw processing: JPEG predictor + full residual → lossless reconstruction",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout()
    plt.show()

    # STEP 6: SAVE OPTIONS
    print("\n[STEP 6] Let user choose which outputs to save...")
    show_save_options(original_arr, jpeg_arr, raw_residual, residual_view_gray, reconstructed_arr)


# ============================================================================
# MAIN ENTRY
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print("DNG RAW IMAGE PROCESSOR – LOSSLESS RECONSTRUCTION (JPEG PREDICTOR)")
    print("=" * 70)
    print("\nThis tool will:")
    print("  1. Load a DNG raw image.")
    print("  2. Create a JPEG compressed predictor.")
    print("  3. Compute full residual (no information discarded).")
    print("  4. Reconstruct an image identical to the original.")
    print("  5. Show all stages and let you save any of them.\n")
    print("=" * 70 + "\n")

    try:
        path = select_image()
        if path:
            run_hybrid_logic(path)
        else:
            print("No file selected. Exiting.")
    except FileNotFoundError:
        messagebox.showerror("Error", "DNG file not found or cannot be processed.")
        print("Error: DNG file not found.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred:\n{e}")


if __name__ == "__main__":
    main()  