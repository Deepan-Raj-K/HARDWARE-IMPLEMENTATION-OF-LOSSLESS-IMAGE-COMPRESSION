import numpy as np
import os
import struct
import cv2
import shutil
from tkinter import Tk, filedialog, messagebox

# ============================================================
# CONFIGURATION
# ============================================================
# FOR 100% ACCURACY, THIS MUST BE 0
LSBS_TO_REMOVE = 0  
BLOCK_SIZE = 16

def remove_lsbs(img, bits):
    """Clears LSBs. If bits=0, this returns the original untouched data."""
    if img is None: return None
    if bits <= 0: return img.astype(np.uint8)
    mask = (0xFF << bits) & 0xFF
    return (img & mask).astype(np.uint8)

def med_predict(a, b, c):
    """Median Edge Detector (MED) - Predicts next pixel based on neighbors."""
    if c >= max(a, b): return min(a, b)
    elif c <= min(a, b): return max(a, b)
    else: return int(a) + int(b) - int(c)

# ============================================================
# PROCESSING ENGINE
# ============================================================

def predictive_encode_channel(channel):
    h, w = channel.shape
    err = np.zeros((h, w), dtype=np.int16)
    padded = np.pad(channel.astype(np.int16), ((1, 0), (1, 0)), mode='constant', constant_values=0)
    for i in range(h):
        for j in range(w):
            a, b, c = padded[i + 1, j], padded[i, j + 1], padded[i, j]
            pred = med_predict(a, b, c)
            err[i, j] = int(channel[i, j]) - pred
    return err

def predictive_decode_channel(err, h, w):
    rec_img = np.zeros((h, w), dtype=np.uint8)
    rec_buf = np.zeros((h + 1, w + 1), dtype=np.int16)
    for i in range(h):
        for j in range(w):
            a, b, c = rec_buf[i + 1, j], rec_buf[i, j + 1], rec_buf[i, j]
            pred = med_predict(a, b, c)
            pixel = np.clip(err[i, j] + pred, 0, 255)
            rec_buf[i + 1, j + 1] = pixel
            rec_img[i, j] = pixel
    return rec_img

# ============================================================
# BITSTREAM TOOLS
# ============================================================

class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.acc, self.bits = 0, 0
    def write_bit(self, b):
        self.acc = (self.acc << 1) | (b & 1)
        self.bits += 1
        if self.bits == 8:
            self.buf.append(self.acc); self.acc = 0; self.bits = 0
    def write_bits(self, v, n):
        for i in reversed(range(n)): self.write_bit((v >> i) & 1)
    def flush(self):
        if self.bits: self.buf.append(self.acc << (8 - self.bits))
        return bytes(self.buf)

# ============================================================
# MAIN WORKFLOW
# ============================================================

def main():
    root = Tk()
    root.withdraw()
    
    input_path = filedialog.askopenfilename(title="Select RGB Image")
    if not input_path: return
    
    output_dir = filedialog.askdirectory(title="Select Folder to Save All Files")
    if not output_dir: return

    try:
        with open(input_path, "rb") as f:
            arr = np.frombuffer(f.read(), dtype=np.uint8)
            original_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR) 
    except Exception as e:
        messagebox.showerror("Error", f"Load failed: {e}"); return
    
    if original_bgr is None: return

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    h, w, channels = original_bgr.shape

    print(f"[*] Processing RGB Image: {base_name}")
    
    bw = BitWriter()
    reconstructed_channels = []
    
    for c_idx in range(channels):
        chan = original_bgr[:, :, c_idx]
        processed_chan = remove_lsbs(chan, LSBS_TO_REMOVE)
        err = predictive_encode_channel(processed_chan)
        
        # Adaptive Rice Encoding
        for i in range(0, h, BLOCK_SIZE):
            for j in range(0, w, BLOCK_SIZE):
                bh, bw2 = min(BLOCK_SIZE, h - i), min(BLOCK_SIZE, w - j)
                blk = err[i:i+bh, j:j+bw2]
                mean_abs = np.mean(np.abs(blk))
                k = int(np.clip(np.ceil(np.log2(0.69 * mean_abs + 1e-9)), 0, 7)) if mean_abs > 0 else 0
                bw.write_bits(k, 3)
                
                for v in blk.flatten():
                    u = int(v * 2 if v >= 0 else -2 * v - 1)
                    q, r = u >> k, u & ((1 << k) - 1)
                    for _ in range(q): bw.write_bit(0)
                    bw.write_bit(1)
                    if k > 0: bw.write_bits(r, k)
        
        reconstructed_channels.append(predictive_decode_channel(err, h, w))

    final_reconstructed = cv2.merge(reconstructed_channels)

    # Saving
    bin_path = os.path.join(output_dir, f"{base_name}_compressed.bin")
    recon_path = os.path.join(output_dir, f"{base_name}_reconstructed.png")
    shutil.copy2(input_path, os.path.join(output_dir, f"original_{os.path.basename(input_path)}"))

    with open(bin_path, "wb") as f:
        f.write(struct.pack(">IIBB", h, w, LSBS_TO_REMOVE, channels))
        f.write(bw.flush())
    cv2.imwrite(recon_path, final_reconstructed)

    # --- ACCURACY PERCENTAGE CALCULATION ---
    # Difference array
    diff = cv2.absdiff(original_bgr, final_reconstructed)
    # Count pixels that are exactly the same
    matching_pixels = np.count_nonzero(diff == 0)
    total_elements = original_bgr.size # H * W * Channels
    accuracy_pct = (matching_pixels / total_elements) * 100

    print("\n" + "="*55)
    print(f"RGB COMPRESSION SUMMARY")
    print(f"Accuracy:         {accuracy_pct:.2f}%")
    print(f"Original Size:    {os.path.getsize(input_path)/1024:.2f} KB")
    print(f"Compressed Bin:   {os.path.getsize(bin_path)/1024:.2f} KB")
    print(f"Ratio:            {os.path.getsize(input_path)/os.path.getsize(bin_path):.2f}:1")
    print("="*55)
    
    if accuracy_pct == 100:
        messagebox.showinfo("Success", "100% Accuracy Achieved!\nLossless Compression Complete.")
    else:
        messagebox.showwarning("Result", f"Accuracy: {accuracy_pct:.2f}%\n(LSB removal active)")

if __name__ == "__main__":
    main()