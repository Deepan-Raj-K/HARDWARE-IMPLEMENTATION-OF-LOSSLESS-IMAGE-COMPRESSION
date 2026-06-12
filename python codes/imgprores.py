import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
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
            # Get basic camera info
            metadata['Camera Make'] = raw.camera_name.split()[0] if raw.camera_name else "Unknown"
            metadata['Camera Model'] = raw.camera_name if raw.camera_name else "Unknown"
            metadata['Sensor Size (H×W)'] = f"{raw.raw_image.shape[0]} × {raw.raw_image.shape[1]}"
            metadata['Color Count'] = raw.color_count
            metadata['Bit Depth'] = f"{raw.bits_per_pixel} bits"
            
            # ISO and exposure data (if available in IFD)
            if hasattr(raw, 'iso_speed'):
                metadata['ISO'] = raw.iso_speed
            if hasattr(raw, 'exposure'):
                metadata['Exposure Time'] = raw.exposure
    except Exception as e:
        print(f"Warning: Could not extract full rawpy metadata: {e}")
    
    # Try to get EXIF data from PIL
    try:
        img = Image.open(path)
        exif_data = img._getexif() if hasattr(img, '_getexif') else None
        
        if exif_data:
            exif_dict = {img.ExifTags.TAGS[k]: v for k, v in exif_data.items() 
                        if k in img.ExifTags.TAGS}
            
            # Common EXIF tags
            if 271 in exif_data:  # Make
                metadata['Make'] = exif_data[271]
            if 272 in exif_data:  # Model
                metadata['Model'] = exif_data[272]
            if 306 in exif_data:  # DateTime
                metadata['DateTime'] = exif_data[306]
            if 34867 in exif_data:  # ISO Speed
                metadata['ISO Speed'] = exif_data[34867]
            if 33434 in exif_data:  # Exposure Time
                metadata['Exposure Time'] = exif_data[33434]
            if 33437 in exif_data:  # F-Number
                metadata['F-Number'] = exif_data[33437]
            if 36867 in exif_data:  # DateTimeOriginal
                metadata['DateTime Original'] = exif_data[36867]
    except Exception as e:
        print(f"Warning: Could not extract PIL EXIF data: {e}")
    
    # File info
    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    metadata['File Size'] = f"{file_size_mb:.2f} MB"
    metadata['File Path'] = path
    
    return metadata


def display_metadata(metadata):
    """Display metadata in a formatted way."""
    print("\n" + "="*70)
    print("DNG IMAGE METADATA")
    print("="*70)
    
    for key, value in metadata.items():
        if key != 'File Path':
            print(f"{key:<25} : {value}")
    
    print(f"\nFull Path: {metadata.get('File Path', 'N/A')}")
    print("="*70 + "\n")
    
    return metadata


# ============================================================================
# IMAGE PROCESSING
# ============================================================================

def load_dng_raw(path):
    """Loads DNG and post-processes it into an RGB array."""
    print("Processing DNG file... this may take a moment.")
    with rawpy.imread(path) as raw:
        # postprocess converts raw sensor data to RGB
        # use_camera_wb=True ensures colors match the camera settings
        rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True, bright=1.0)
    return rgb


def create_metadata_display(metadata):
    """Create a visual display of metadata as an image."""
    # Create a white background image
    img_width = 800
    img_height = 300
    background = Image.new('RGB', (img_width, img_height), color='white')
    
    # Add text to the image
    draw = ImageDraw.Draw(background)
    
    try:
        # Try to use a nice font, fallback to default if not available
        font = ImageFont.truetype("arial.ttf", 11)
        title_font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    # Draw title
    draw.text((20, 10), "DNG IMAGE METADATA", fill='black', font=title_font)
    draw.line([(20, 35), (780, 35)], fill='black', width=2)
    
    # Draw metadata in two columns
    x_left = 25
    x_right = 420
    left_y = 50
    right_y = 50
    column = 0
    
    for key, value in metadata.items():
        if key != 'File Path':
            text = f"{key}: {str(value)[:40]}"
            
            if column == 0:
                draw.text((x_left, left_y), text, fill='black', font=font)
                left_y += 22
                if left_y > 280:
                    column = 1
                    left_y = 50
            else:
                draw.text((x_right, right_y), text, fill='black', font=font)
                right_y += 22
    
    return np.array(background)


# ============================================================================
# FILE SAVING
# ============================================================================

def save_multiple_formats(original_arr, jpeg_arr, residual_view_gray, reconstructed_arr, metadata):
    """Save all four images (Original, JPEG, Residual, Reconstructed) with timestamps and metadata."""
    root = tk.Tk()
    root.withdraw()
    
    # Ask user where to save
    folder_path = filedialog.askdirectory(
        title="Select folder to save all images"
    )
    
    if not folder_path:
        print("Save cancelled.")
        root.destroy()
        return
    
    # Create timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # 1. Save Original (as PNG - lossless)
        original_path = os.path.join(folder_path, f"01_Original_Raw_{timestamp}.png")
        Image.fromarray(original_arr).save(original_path, format="PNG")
        print(f"✓ Original saved: {original_path}")
        
        # 2. Save JPEG (compressed version)
        jpeg_path = os.path.join(folder_path, f"02_Compressed_JPEG_{timestamp}.jpg")
        Image.fromarray(jpeg_arr).save(jpeg_path, format="JPEG", quality=90)
        print(f"✓ JPEG saved: {jpeg_path}")
        
        # 3. Save Residual (difference map, filtered & quantized, grayscale)
        residual_path = os.path.join(folder_path, f"03_Residual_Difference_{timestamp}.png")
        Image.fromarray(residual_view_gray).save(residual_path, format="PNG")
        print(f"✓ Residual saved: {residual_path}")
        
        # 4. Save Reconstructed (from JPEG + quantized residual)
        reconstructed_path = os.path.join(folder_path, f"04_Reconstructed_Lossy_{timestamp}.png")
        Image.fromarray(reconstructed_arr).save(reconstructed_path, format="PNG")
        print(f"✓ Reconstructed saved: {reconstructed_path}")
        
        # 5. Save Metadata as text file
        metadata_path = os.path.join(folder_path, f"00_Metadata_{timestamp}.txt")
        with open(metadata_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("DNG RAW IMAGE PROCESSING REPORT\n")
            f.write("="*70 + "\n\n")
            f.write("METADATA:\n")
            f.write("-"*70 + "\n")
            for key, value in metadata.items():
                if key != 'File Path':
                    f.write(f"{key:<30} : {value}\n")
            f.write(f"\n{'Full Path':<30} : {metadata.get('File Path', 'N/A')}\n")
            f.write("\n" + "="*70 + "\n")
            f.write("PROCESSING SUMMARY:\n")
            f.write("-"*70 + "\n")
            f.write(f"Processing Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Original Image Size: {original_arr.shape}\n")
            f.write(f"JPEG Quality: 90%\n")
            f.write("\n" + "="*70 + "\n")
            f.write("FILES SAVED:\n")
            f.write("-"*70 + "\n")
            f.write(f"✓ 01_Original_Raw_{timestamp}.png\n")
            f.write(f"✓ 02_Compressed_JPEG_{timestamp}.jpg\n")
            f.write(f"✓ 03_Residual_Difference_{timestamp}.png\n")
            f.write(f"✓ 04_Reconstructed_Lossy_{timestamp}.png\n")
            f.write(f"✓ 00_Metadata_{timestamp}.txt\n")
            f.write("="*70 + "\n")
        
        print(f"✓ Metadata saved: {metadata_path}")
        
        print(f"\n[SUCCESS] All images and metadata saved to: {folder_path}")
        
        # Open the folder automatically
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # Mac
                subprocess.Popen(['open', folder_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            print(f"Could not open folder automatically: {e}")
        
        messagebox.showinfo(
            "Success",
            f"All files saved to:\n{folder_path}\n\n"
            "✓ Original (PNG)\n"
            "✓ JPEG Compressed (JPG)\n"
            "✓ Residual Map (PNG)\n"
            "✓ Reconstructed (PNG)\n"
            "✓ Metadata Report (TXT)"
        )
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save images: {e}")
        print(f"Error during save: {e}")
    
    root.destroy()


# ============================================================================
# MAIN PROCESSING LOGIC
# ============================================================================

def run_hybrid_logic(image_path):
    """Main processing logic: Load DNG, compress to JPEG, calculate residual (filtered/quantized), reconstruct."""
    if not image_path:
        print("No file selected.")
        return

    print(f"\n{'='*70}")
    print(f"Reading DNG file: {image_path}")
    print(f"{'='*70}\n")
    
    # STEP 0: EXTRACT METADATA
    print("[STEP 0] Extracting metadata...")
    metadata = get_dng_metadata(image_path)
    display_metadata(metadata)
    
    # 1. LOAD RAW DATA
    print("[STEP 1] Loading raw DNG data...")
    original_arr = load_dng_raw(image_path)
    original_arr = np.clip(original_arr, 0, 255).astype(np.uint8)
    print(f"✓ Original shape: {original_arr.shape}, dtype: {original_arr.dtype}")
    
    # 2. GENERATE JPEG PREDICTOR (Compressed version)
    print("\n[STEP 2] Generating JPEG compressed version...")
    buffer = io.BytesIO()
    Image.fromarray(original_arr).save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    jpeg_arr = np.array(Image.open(buffer))
    print(f"✓ JPEG shape: {jpeg_arr.shape}, dtype: {jpeg_arr.dtype}")

    # 3. CALCULATE RESIDUAL WITH THRESHOLD + QUANTIZATION
    print("\n[STEP 3] Calculating filtered & quantized residual...")
    raw_residual = original_arr.astype(np.int16) - jpeg_arr.astype(np.int16)
    abs_residual = np.abs(raw_residual)

    # Threshold: keep only significant differences
    threshold = 4  # you can tune this
    mask = abs_residual >= threshold
    raw_residual_filtered = np.where(mask, raw_residual, 0)

    # Quantize residual to reduce precision (and entropy)
    step = 2  # you can tune this
    raw_residual_quantized = (raw_residual_filtered // step) * step

    # For visualization: grayscale view of the quantized residual
    abs_residual_quantized = np.abs(raw_residual_quantized).astype(np.uint8)
    max_val = abs_residual_quantized.max()
    if max_val > 0:
        residual_view_gray = (abs_residual_quantized.astype(np.float32) / max_val * 255).astype(
            np.uint8
        )
    else:
        residual_view_gray = abs_residual_quantized

    print(f"✓ Residual shape: {raw_residual.shape}")
    print(f"✓ Max residual difference (before filtering): {abs_residual.max()}")
    print(f"✓ Max residual difference (after filtering/quantization): {abs_residual_quantized.max()}")
    print(f"✓ Non-zero residual pixels after filtering: {np.count_nonzero(raw_residual_quantized)}")

    # 4. RECONSTRUCT (USING FILTERED + QUANTIZED RESIDUAL)
    print("\n[STEP 4] Reconstructing image from JPEG + quantized residual...")
    reconstructed_arr = np.clip(
        jpeg_arr.astype(np.int16) + raw_residual_quantized,
        0,
        255,
    ).astype(np.uint8)
    print(f"✓ Reconstructed shape: {reconstructed_arr.shape}")
    
    # Verify reconstruction quality (not lossless now, but reduced residual)
    mse = np.mean(
        (original_arr.astype(np.float32) - reconstructed_arr.astype(np.float32)) ** 2
    )
    print(f"✓ MSE (Original vs Reconstructed with reduced residual): {mse:.6f}")

    # --- VISUALIZATION WITH CLEANER LAYOUT ---
    print("\n[STEP 5] Displaying comparison with metadata...")
    
    metadata_img = create_metadata_display(metadata)

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25)

    # Metadata
    ax_meta = fig.add_subplot(gs[0, :])
    ax_meta.imshow(metadata_img)
    ax_meta.set_title("Metadata Information", fontweight="bold", fontsize=13)
    ax_meta.axis("off")

    # Original
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.imshow(original_arr)
    ax1.set_title("Original (Raw → RGB)", fontweight="bold", fontsize=11)
    ax1.axis("off")

    # JPEG
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.imshow(jpeg_arr)
    ax2.set_title("Compressed (JPEG Q=90)", fontweight="bold", fontsize=11)
    ax2.axis("off")

    # Residual (filtered & quantized, grayscale)
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.imshow(residual_view_gray, cmap="gray")
    ax3.set_title("Residual (Significant Differences)", fontweight="bold", fontsize=11)
    ax3.axis("off")

    # Reconstructed
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.imshow(reconstructed_arr)
    ax4.set_title("Reconstructed (JPEG + Reduced Residual)", fontweight="bold", fontsize=11)
    ax4.axis("off")

    fig.suptitle(
        "DNG Raw Processing: Metadata + Original / JPEG / Residual / Reconstructed",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout()
    plt.show()

    # --- SAVE ALL IMAGES AND METADATA ---
    print("\n[STEP 6] Saving all images and metadata...")
    save_multiple_formats(original_arr, jpeg_arr, residual_view_gray, reconstructed_arr, metadata)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point of the application."""
    print("\n" + "="*70)
    print("DNG RAW IMAGE PROCESSOR WITH METADATA & REDUCED RESIDUAL")
    print("="*70)
    print("\nThis tool will:")
    print("  1. Load a DNG raw image from your camera")
    print("  2. Extract and display metadata (Camera, ISO, Exposure, etc.)")
    print("  3. Process the image through hybrid compression logic:")
    print("     • Original: Raw sensor data converted to RGB")
    print("     • JPEG: Compressed version (Q=90)")
    print("     • Residual: Filtered & quantized difference map")
    print("     • Reconstructed: JPEG + reduced residual")
    print("  4. Display all results visually in a clean layout")
    print("  5. Save Original (PNG), JPEG, Residual (PNG), Reconstructed (PNG)")
    print("  6. Save a metadata report (TXT)")
    print("\n" + "="*70 + "\n")
    
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


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    main()
