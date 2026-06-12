import numpy as np
import tkinter as tk
from tkinter import filedialog
from PIL import Image

def select_file(title):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
    root.destroy()
    return path

def compare_images():
    # 1. Select the two images
    print("Select the first image (e.g., Original)...")
    path1 = select_file("Select First Image")
    if not path1: return

    print("Select the second image (e.g., Reconstructed)...")
    path2 = select_file("Select Second Image")
    if not path2: return

    # 2. Load images and ensure they are the same format
    img1 = np.array(Image.open(path1).convert("RGB"))
    img2 = np.array(Image.open(path2).convert("RGB"))

    # 3. Check dimensions
    if img1.shape != img2.shape:
        print(f"Error: Dimensions mismatch!")
        print(f"Image 1: {img1.shape}")
        print(f"Image 2: {img2.shape}")
        return

    # 4. Calculate Pixel-by-Pixel Accuracy
    # We create a boolean array where True means the pixels are identical
    comparison = (img1 == img2)
    
    # Each pixel has 3 values (R, G, B). 
    # A 'Correct' pixel is one where all three channels match.
    matching_pixels = np.all(comparison, axis=-1)
    
    total_pixels = matching_pixels.size
    correct_count = np.count_nonzero(matching_pixels)
    
    accuracy = (correct_count / total_pixels) * 100

    # 5. Calculate Average Error (MAE)
    # This tells you how 'far off' the wrong pixels are on average
    abs_diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))
    mean_error = np.mean(abs_diff)

    print("-" * 30)
    print(f"Comparison Results:")
    print(f"Total Pixels    : {total_pixels:,}")
    print(f"Exact Matches   : {correct_count:,}")
    print(f"Accuracy        : {accuracy:.4f} %")
    print(f"Mean Pixel Error: {mean_error:.4f} (0 is perfect)")
    print("-" * 30)

if __name__ == "__main__":
    compare_images()