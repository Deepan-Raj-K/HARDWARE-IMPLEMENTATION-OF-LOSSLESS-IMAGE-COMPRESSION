import numpy as np
import rawpy
from tkinter import Tk, filedialog

# ============================================================
# FILE SELECT
# ============================================================

def select_file():
    Tk().withdraw()
    return filedialog.askopenfilename()


# ============================================================
# LOAD RAW / DNG
# ============================================================

def load_raw(path):
    with rawpy.imread(path) as raw:
        img = raw.raw_image.copy()
    return img.astype(np.uint16)


# ============================================================
# MED PREDICTOR
# ============================================================

def med_predict(A, B, C):
    if C >= max(A, B):
        return min(A, B)
    elif C <= min(A, B):
        return max(A, B)
    else:
        return A + B - C


# ============================================================
# SIGNED <-> UNSIGNED
# ============================================================

def signed_to_unsigned(e):
    return 2*e if e >= 0 else -2*e - 1

def unsigned_to_signed(u):
    return u//2 if u % 2 == 0 else -(u//2) - 1


# ============================================================
# RICE
# ============================================================

def rice_encode(val, k):
    q = val >> k
    r = val & ((1 << k) - 1)

    bits = [0]*q + [1]

    for i in reversed(range(k)):
        bits.append((r >> i) & 1)

    return bits


def rice_decode(bits, idx, k):
    q = 0
    while idx < len(bits) and bits[idx] == 0:
        q += 1
        idx += 1

    if idx >= len(bits):
        raise ValueError("Corrupt unary")

    idx += 1  # skip 1

    r = 0
    for _ in range(k):
        if idx >= len(bits):
            raise ValueError("Corrupt remainder")
        r = (r << 1) | bits[idx]
        idx += 1

    return (q << k) | r, idx


# ============================================================
# COMPUTE BLOCK K
# ============================================================

def compute_k(block_vals):
    mean = np.mean(block_vals)
    if mean <= 1:
        return 0
    return int(np.floor(np.log2(mean + 1e-9)))


# ============================================================
# ENCODE (BLOCK BASED)
# ============================================================

def encode(img, block_size=64):

    h, w = img.shape
    residuals = np.zeros_like(img, dtype=np.int32)

    # ---- Stage 1: MED residual ----
    for i in range(h):
        for j in range(w):

            if i == 0 and j == 0:
                pred = 0
            elif i == 0:
                pred = img[i, j-1]
            elif j == 0:
                pred = img[i-1, j]
            else:
                A = img[i, j-1]
                B = img[i-1, j]
                C = img[i-1, j-1]
                pred = med_predict(A, B, C)

            residuals[i, j] = int(img[i, j]) - int(pred)

    # ---- Stage 2: Block Rice ----
    bits = []

    for bi in range(0, h, block_size):
        for bj in range(0, w, block_size):

            block = residuals[bi:bi+block_size, bj:bj+block_size]

            # map to unsigned
            unsigned_block = np.vectorize(signed_to_unsigned)(block)

            flat = unsigned_block.flatten()

            k = compute_k(flat)

            # store k (5 bits)
            for b in reversed(range(5)):
                bits.append((k >> b) & 1)

            for val in flat:
                bits.extend(rice_encode(int(val), k))

    return bits


# ============================================================
# DECODE
# ============================================================

def decode(bits, h, w, block_size=64):

    residuals = np.zeros((h, w), dtype=np.int32)

    idx = 0

    # ---- Stage 2: Rice Decode ----
    for bi in range(0, h, block_size):
        for bj in range(0, w, block_size):

            # read k
            k = 0
            for _ in range(5):
                k = (k << 1) | bits[idx]
                idx += 1

            for i in range(bi, min(bi+block_size, h)):
                for j in range(bj, min(bj+block_size, w)):
                    val, idx = rice_decode(bits, idx, k)
                    residuals[i, j] = unsigned_to_signed(val)

    # ---- Stage 1: Reconstruct ----
    recon = np.zeros((h, w), dtype=np.uint16)

    for i in range(h):
        for j in range(w):

            if i == 0 and j == 0:
                pred = 0
            elif i == 0:
                pred = recon[i, j-1]
            elif j == 0:
                pred = recon[i-1, j]
            else:
                A = recon[i, j-1]
                B = recon[i-1, j]
                C = recon[i-1, j-1]
                pred = med_predict(A, B, C)

            recon[i, j] = np.uint16(int(pred) + residuals[i, j])

    return recon


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    path = select_file()
    raw = load_raw(path)

    h, w = raw.shape
    print("RAW shape:", raw.shape)

    bits = encode(raw, block_size=64)
    recon = decode(bits, h, w, block_size=64)

    original_mb = raw.nbytes / (1024*1024)
    compressed_mb = len(bits) / 8 / (1024*1024)

    print("Lossless:", np.array_equal(raw, recon))
    print("Original MB:", original_mb)
    print("Compressed MB:", compressed_mb)
    print("Bits per pixel:", len(bits)/(h*w))

    diff = recon.astype(np.int32) - raw.astype(np.int32)
    print("Max abs error:", np.max(np.abs(diff)))
    print("Non-zero error count:", np.count_nonzero(diff))
