import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import matplotlib.pyplot as plt

def select_file(title, filetypes):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return path

def reconstruct():
    # 1. Manually Select the Files
    print("Select the JPEG Base file...")
    jpeg_path = select_file("Select JPEG Base", [("JPEG Files", "*.jpg")])
    if not jpeg_path: return

    print("Select the Residual PNG file...")
    residual_path = select_file("Select Residual PNG", [("PNG Files", "*.png")])
    if not residual_path: return

    # 2. Load the images
    # We use .convert("RGB") to ensure we have 3 channels
    jpeg_img = np.array(Image.open(jpeg_path).convert("RGB")).astype(np.int16)
    residual_img = np.array(Image.open(residual_path).convert("RGB")).astype(np.int16)

    # Check if sizes match
    if jpeg_img.shape != residual_img.shape:
        messagebox.showerror("Error", "Image dimensions do not match!")
        return

    # 3. RECONSTRUCTION MATH
    # Subtract 128 to shift the mid-gray back to zero
    # Then add the residual back to the JPEG
    print("Reconstructing...")
    reconstructed = jpeg_img + (residual_img - 128)

    # Clip values to ensure they stay in the 0-255 range and convert back to uint8
    reconstructed = np.clip(reconstructed, 0, 255).astype(np.uint8)

    # 4. SAVE AND DISPLAY
    final_img = Image.fromarray(reconstructed)
    final_img.save("reconstructed_output.png")
    
    print("Success! Saved as 'reconstructed_output.png'")

    # Show comparison
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    plt.imshow(jpeg_img.astype(np.uint8))
    plt.title("Base JPEG (Lossy)")
    plt.axis('off')

    plt.subplot(1, 2, 2)
    plt.imshow(reconstructed)
    plt.title("Reconstructed (Detail Restored)")
    plt.axis('off')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    reconstruct()