import numpy as np
import os
import struct
import cv2
from tkinter import Tk, filedialog, messagebox
import rawpy


# ============================================================
# SAVE FUNCTIONS (EXPLICIT AND CLEAN)
# ============================================================

def save_original(gray, name):
    filename = f"{name}_original_gray.png"
    cv2.imwrite(filename, gray)
    return filename


def save_residual_bin(bitstream, h, w, name):
    filename = f"{name}_residual_med_rice.bin"
    with open(filename, "wb") as f:
        f.write(struct.pack("II", h, w))
        f.write(bitstream)
    return filename


def save_reconstructed(rec, name):
    filename = f"{name}_reconstructed_gray.png"
    cv2.imwrite(filename, rec)
    return filename


# ============================================================
# LOAD RAW OR IMAGE → GRAYSCALE
# ============================================================

def load_image_gray(path):
    ext = os.path.splitext(path)[1].lower()

    if ext in [".dng", ".arw", ".nef", ".cr2", ".rw2"]:
        print("Loading RAW file with rawpy...")
        try:
            with rawpy.imread(path) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=True,
                    bright=1.0,
                    output_bps=8
                )
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        except Exception as e:
            raise RuntimeError(f"Failed to load RAW file: {e}")

        return gray.astype(np.uint8)

    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError("Failed to load image.")
    return img.astype(np.uint8)


# ============================================================
# MED PREDICTOR
# ============================================================

def med_predict(a, b, c):
    if c >= max(a, b):
        return min(a, b)
    elif c <= min(a, b):
        return max(a, b)
    else:
        return a + b - c


def predictive_encode(img):
    h, w = img.shape
    err = np.zeros_like(img, dtype=np.int16)

    for i in range(h):
        for j in range(w):
            a = img[i, j-1] if j > 0 else 0
            b = img[i-1, j] if i > 0 else 0
            c = img[i-1, j-1] if (i > 0 and j > 0) else 0
            pred = med_predict(a, b, c)
            err[i, j] = int(img[i, j]) - int(pred)

    return err


def predictive_decode(err):
    h, w = err.shape
    img = np.zeros_like(err, dtype=np.int16)

    for i in range(h):
        for j in range(w):
            a = img[i, j-1] if j > 0 else 0
            b = img[i-1, j] if i > 0 else 0
            c = img[i-1, j-1] if (i > 0 and j > 0) else 0
            pred = med_predict(a, b, c)
            img[i, j] = err[i, j] + pred

    return img


# ============================================================
# RICE CODING
# ============================================================

def signed_to_unsigned(v):
    return v * 2 if v >= 0 else -2 * v - 1


def unsigned_to_signed(u):
    return u // 2 if (u & 1) == 0 else -(u // 2) - 1


class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.acc = 0
        self.bits = 0

    def write_bit(self, b):
        self.acc = (self.acc << 1) | b
        self.bits += 1
        if self.bits == 8:
            self.buf.append(self.acc)
            self.acc = 0
            self.bits = 0

    def write_bits(self, v, n):
        for i in reversed(range(n)):
            self.write_bit((v >> i) & 1)

    def flush(self):
        if self.bits:
            self.acc <<= (8 - self.bits)
            self.buf.append(self.acc)
        return bytes(self.buf)


class BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.acc = 0
        self.bits = 0

    def read_bit(self):
        if self.bits == 0:
            self.acc = self.data[self.pos]
            self.pos += 1
            self.bits = 8
        self.bits -= 1
        return (self.acc >> self.bits) & 1

    def read_bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | self.read_bit()
        return v


def choose_k(block):
    mean = np.mean(np.abs(block))
    if mean < 1: return 0
    if mean < 2: return 1
    if mean < 4: return 2
    if mean < 8: return 3
    if mean < 16: return 4
    return 5


def rice_encode(err, bw, block=16):
    h, w = err.shape
    for i in range(0, h, block):
        for j in range(0, w, block):
            bh = min(block, h - i)
            bw2 = min(block, w - j)
            blk = err[i:i+bh, j:j+bw2]
            k = choose_k(blk)
            bw.write_bits(k, 3)

            for v in blk.flatten():
                u = signed_to_unsigned(int(v))
                q = u >> k
                r = u & ((1 << k) - 1)

                for _ in range(q):
                    bw.write_bit(0)
                bw.write_bit(1)
                if k > 0:
                    bw.write_bits(r, k)


def rice_decode(br, shape, block=16):
    h, w = shape
    err = np.zeros((h, w), dtype=np.int16)

    for i in range(0, h, block):
        for j in range(0, w, block):
            bh = min(block, h - i)
            bw2 = min(block, w - j)
            n = bh * bw2

            k = br.read_bits(3)
            flat = np.zeros(n, dtype=np.int16)

            for idx in range(n):
                q = 0
                while br.read_bit() == 0:
                    q += 1
                r = br.read_bits(k) if k > 0 else 0
                u = (q << k) | r
                flat[idx] = unsigned_to_signed(u)

            err[i:i+bh, j:j+bw2] = flat.reshape((bh, bw2))

    return err


# ============================================================
# MAIN GRAYSCALE LOSSLESS CODEC (WITH CLEAN SAVE FUNCTIONS)
# ============================================================

def main():
    Tk().withdraw()
    path = filedialog.askopenfilename(title="Select RAW or grayscale image")

    if not path:
        print("No file selected.")
        return

    name = os.path.splitext(os.path.basename(path))[0]

    try:
        gray = load_image_gray(path)
    except Exception as e:
        messagebox.showerror("Error", str(e))
        print("[ERROR]", e)
        return

    h, w = gray.shape
    N = h * w

    # --------------------------------------------------------
    # SAVE ORIGINAL
    # --------------------------------------------------------

    original_file = save_original(gray, name)

    # --------------------------------------------------------
    # ENCODE
    # --------------------------------------------------------

    print("\n[STEP 1] MED predictive encoding...")
    err = predictive_encode(gray)

    max_err = np.max(np.abs(err))
    mean_err = np.mean(np.abs(err))

    print("[STEP 2] Adaptive Rice coding...")
    bw = BitWriter()
    rice_encode(err, bw)
    bitstream = bw.flush()

    residual_file = save_residual_bin(bitstream, h, w, name)

    # --------------------------------------------------------
    # DECODE & RECONSTRUCT
    # --------------------------------------------------------

    print("[STEP 3] Decoding and reconstructing...")

    with open(residual_file, "rb") as f:
        h2, w2 = struct.unpack("II", f.read(8))
        data = f.read()

    br = BitReader(data)
    decErr = rice_decode(br, (h, w))
    rec = predictive_decode(decErr)
    rec = np.clip(rec, 0, 255).astype(np.uint8)

    recon_file = save_reconstructed(rec, name)

    # --------------------------------------------------------
    # REPORT (ONLY RESIDUAL COUNTS)
    # --------------------------------------------------------

    s_orig = os.path.getsize(original_file)
    s_res = os.path.getsize(residual_file)
    s_rec = os.path.getsize(recon_file)

    bits_per_pixel = (s_res * 8) / N
    perfect = np.array_equal(gray, rec)

    print("\n" + "=" * 85)
    print("PURE MED + ADAPTIVE RICE GRAYSCALE LOSSLESS SUMMARY (PREDICTOR IMPLICIT)")
    print("=" * 85)
    print(f"Image size (HxW)        : {h} x {w}")
    print(f"Total pixels           : {N}")
    print(f"Max residual           : {max_err}")
    print(f"Mean abs residual      : {mean_err:.6f}")
    print(f"Original PNG size      : {s_orig/1024:.2f} KB")
    print(f"Residual file size     : {s_res/1024:.2f} KB")
    print(f"Reconstructed PNG size : {s_rec/1024:.2f} KB")
    print(f"Bits per pixel (bpp)   : {bits_per_pixel:.4f}")
    print(f"Pixel-perfect recon   : {perfect}")
    print("=" * 85 + "\n")

    if not perfect:
        print("Max reconstruction error:",
              int(np.abs(gray.astype(int) - rec.astype(int)).max()))


if __name__ == "__main__":
    main()