import numpy as np
import cv2
import os
import math
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

# ==========================
# USER PARAMETERS
# ==========================
BPP = 8
S = 4

# ==========================
# UTILITY FUNCTIONS
# ==========================

def msb_pos(val):
    if val <= 0:
        return 0
    return int(np.floor(np.log2(val)))

def signed_to_unsigned(e):
    return 2*e if e >= 0 else -2*e - 1

def unsigned_to_signed(u):
    return u//2 if u % 2 == 0 else -(u//2) - 1

def compute_psnr(original, recon):
    mse = np.mean((original.astype(np.float64) - recon.astype(np.float64))**2)
    if mse == 0:
        return float("inf")
    max_val = (1 << BPP) - 1
    return 10 * np.log10((max_val**2) / mse)

def compute_entropy(data):
    hist = np.bincount(data.flatten())
    prob = hist / np.sum(hist)
    prob = prob[prob > 0]
    return -np.sum(prob * np.log2(prob))

# ==========================
# MED Predictor
# ==========================

def med_predict(A, B, C):

    if C >= max(A, B):
        return min(A, B)

    elif C <= min(A, B):
        return max(A, B)

    else:
        return A + B - C


# ==========================
# BIT WRITER
# ==========================

class BitWriter:

    def __init__(self, filename):

        self.file = open(filename, "wb")
        self.buffer = 0
        self.count = 0
        self.total_bits = 0

    def write_bit(self, bit):

        self.buffer = (self.buffer << 1) | bit
        self.count += 1
        self.total_bits += 1

        if self.count == 8:

            self.file.write(bytes([self.buffer]))
            self.buffer = 0
            self.count = 0

    def write_bits(self, value, n):

        for i in reversed(range(n)):
            self.write_bit((value >> i) & 1)

    def close(self):

        if self.count > 0:
            self.buffer <<= (8 - self.count)
            self.file.write(bytes([self.buffer]))

        self.file.close()


# ==========================
# BIT READER
# ==========================

class BitReader:

    def __init__(self, filename):

        self.file = open(filename, "rb")
        self.buffer = 0
        self.count = 0

    def read_bit(self):

        if self.count == 0:

            byte = self.file.read(1)

            if not byte:
                return None

            self.buffer = byte[0]
            self.count = 8

        self.count -= 1

        return (self.buffer >> self.count) & 1

    def read_bits(self, n):

        val = 0

        for _ in range(n):

            bit = self.read_bit()

            if bit is None:
                return None

            val = (val << 1) | bit

        return val

    def close(self):

        self.file.close()


# ==========================
# RICE CODING
# ==========================

def rice_encode(writer, value, k):

    q = value >> k
    r = value & ((1 << k) - 1)

    for _ in range(q):
        writer.write_bit(1)

    writer.write_bit(0)

    if k > 0:
        writer.write_bits(r, k)


def rice_decode(reader, k):

    q = 0

    while True:

        bit = reader.read_bit()

        if bit == 0:
            break

        q += 1

    r = reader.read_bits(k) if k > 0 else 0

    return (q << k) | r


# ==========================
# ENCODER
# ==========================

def encode(image, binfile):

    h, w = image.shape

    writer = BitWriter(binfile)

    recon = np.zeros((h, w), dtype=np.int32)
    residuals = []

    A_est = 4
    k = msb_pos(A_est)

    for y in range(h):

        for x in range(w):

            X = int(image[y, x])

            A = recon[y, x-1] if x > 0 else 0
            B = recon[y-1, x] if y > 0 else 0
            C = recon[y-1, x-1] if (x > 0 and y > 0) else 0

            X_hat = med_predict(A, B, C)

            E = X - X_hat
            U = signed_to_unsigned(E)

            rice_encode(writer, U, k)

            residuals.append(U)

            pixel = X_hat + E
            pixel = max(0, min((1 << BPP)-1, pixel))

            recon[y, x] = pixel

            diff = U - A_est
            A_est = max(1, A_est + (diff >> S))
            k = msb_pos(A_est)

    writer.close()

    return np.array(residuals), writer.total_bits


# ==========================
# DECODER
# ==========================

def decode(width, height, binfile):

    reader = BitReader(binfile)

    recon = np.zeros((height, width), dtype=np.int32)

    A_est = 4
    k = msb_pos(A_est)

    for y in range(height):

        for x in range(width):

            U = rice_decode(reader, k)

            E = unsigned_to_signed(U)

            A = recon[y, x-1] if x > 0 else 0
            B = recon[y-1, x] if y > 0 else 0
            C = recon[y-1, x-1] if (x > 0 and y > 0) else 0

            X_hat = med_predict(A, B, C)

            pixel = X_hat + E
            pixel = max(0, min((1 << BPP)-1, pixel))

            recon[y, x] = pixel

            diff = U - A_est
            A_est = max(1, A_est + (diff >> S))
            k = msb_pos(A_est)

    reader.close()

    return recon


# ==========================
# IMAGE LOADER
# ==========================

def load_image(path):

    ext = path.split(".")[-1].lower()

    if ext == "heic":

        img = Image.open(path)
        img = np.array(img)

    else:

        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    if len(img.shape) > 2:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return img


# ==========================
# MAIN PIPELINE
# ==========================

def process_image(path):

    print("\n======================================")
    print("Processing:", path)

    img = load_image(path)

    h, w = img.shape

    print("Resolution:", w, "x", h)
    print("Max Pixel:", img.max())

    binfile = "compressed_output.bin"

    residuals, compressed_bits = encode(img, binfile)

    recon = decode(w, h, binfile)

    # Match original dtype
    recon = recon.astype(img.dtype)

    ext = path.split(".")[-1]
    recon_name = "reconstructed." + ext

    if ext == "heic":

        Image.fromarray(recon).save(recon_name)

    else:

        cv2.imwrite(recon_name, recon)

    psnr = compute_psnr(img, recon)

    entropy_original = compute_entropy(img)
    entropy_residual = compute_entropy(residuals)

    original_bits = img.size * BPP
    ratio = original_bits / compressed_bits

    print("Compression Ratio:", ratio)
    print("PSNR:", psnr)

    bpp = compressed_bits / img.size
    print("Bits per pixel:", bpp)

    print("Original Entropy:", entropy_original)
    print("Residual Entropy:", entropy_residual)

    print("Compressed Size (bytes):", os.path.getsize(binfile))
    print("Saved reconstructed:", recon_name)

    print("======================================")


# ==========================
# RUN FOR MULTIPLE FORMATS
# ==========================

if __name__ == "__main__":

    images = [
        "original_png.png",
        "original_jpg.jpg",
        "original_bmp.bmp",
        "original_tiff.tiff",
        "original_heic.heic"
    ]

    for img in images:

        if os.path.exists(img):
            process_image(img)