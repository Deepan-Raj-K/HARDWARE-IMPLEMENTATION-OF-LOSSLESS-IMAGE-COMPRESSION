import numpy as np
import cv2
import os
import math

# ==========================
# USER PARAMETERS
# ==========================
BPP = 16              # Container bit depth (8,10,12,16)
S   = 4               # Adaptation shift (match RTL)
BIN_FILE   = "compressed_output.bin"
RECON_FILE = "reconstructed.png"

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
    mse = np.mean((original.astype(np.float64) -
                   recon.astype(np.float64)) ** 2)
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
# MED PREDICTOR (JPEG-LS)
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

def encode(image):

    h, w = image.shape
    writer = BitWriter(BIN_FILE)

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
            max_val = (1 << BPP) - 1
            pixel = max(0, min(max_val, pixel))
            recon[y, x] = pixel

            diff = U - A_est
            A_est = max(1, A_est + (diff >> S))
            k = msb_pos(A_est)

    writer.close()

    original_bits = h * w * BPP
    compressed_bits = writer.total_bits
    ratio = original_bits / compressed_bits

    print("Encoding complete.")
    print("Original bits:", original_bits)
    print("Compressed bits:", compressed_bits)
    print("Compression ratio:", ratio)

    return np.array(residuals), original_bits, compressed_bits

# ==========================
# DECODER
# ==========================

def decode(width, height):

    reader = BitReader(BIN_FILE)
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
            max_val = (1 << BPP) - 1
            pixel = max(0, min(max_val, pixel))

            recon[y, x] = pixel

            diff = U - A_est
            A_est = max(1, A_est + (diff >> S))
            k = msb_pos(A_est)

    reader.close()

    dtype = np.uint8 if BPP <= 8 else np.uint16
    recon_out = recon.astype(dtype)

    cv2.imwrite(RECON_FILE, recon_out)
    print("Reconstructed image saved.")

    return recon_out

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    img = cv2.imread("original.png", cv2.IMREAD_UNCHANGED)

    if img is None:
        print("Error: original.png not found")
        exit()

    if len(img.shape) > 2:
        print("Convert to grayscale first.")
        exit()

    h, w = img.shape

    print("Image dtype:", img.dtype)
    print("Max pixel value:", img.max())

    # Effective BPP (for information only)
    detected_bpp = int(math.ceil(math.log2(img.max() + 1)))
    print("Detected effective BPP:", detected_bpp)

    residuals, original_bits, compressed_bits = encode(img)
    recon = decode(w, h)

    if np.array_equal(img, recon):
        print("✅ Pixel Perfect Reconstruction!")
    else:
        print("❌ NOT Pixel Perfect!")

    psnr = compute_psnr(img, recon)
    print("PSNR:", psnr)

    entropy_original = compute_entropy(img)
    entropy_residual = compute_entropy(residuals)

    print("Original entropy:", entropy_original)
    print("Residual entropy:", entropy_residual)

    compressed_size = os.path.getsize(BIN_FILE)
    original_size = img.size * (BPP / 8)

    print("Compressed file size (bytes):", compressed_size)
    print("Estimated original size (bytes):", original_size)