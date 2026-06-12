import numpy as np
import os

# ==========================
# USER PARAMETERS
# ==========================
WIDTH  = 512
HEIGHT = 512
BPP = 8
S = 4

INPUT_HEX  = "F:/Documents/Academics/mini project/pre and post processing/misc/top10/img12.hex"          # original reference
INPUT_BIN  = "F:/Documents/Academics/mini project/pre and post processing/misc/top10/img12.bin"   # compressed file
RECON_HEX  = "F:/Documents/Academics/mini project/pre and post processing/misc/top10/reconstructed.hex"


# ==========================
# UTILS
# ==========================

def msb_pos(val):
    if val <= 0:
        return 0
    return int(np.floor(np.log2(val)))

def unsigned_to_signed(u):
    return u//2 if u % 2 == 0 else -(u//2) - 1


# ==========================
# MED PREDICTOR
# ==========================

def med_predict(A, B, C):
    if C >= max(A, B):
        return min(A, B)
    elif C <= min(A, B):
        return max(A, B)
    else:
        return A + B - C


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

        bit = (self.buffer >> 7) & 1
        self.buffer <<= 1
        self.count -= 1
        return bit

    def read_bits(self, n):
        val = 0
        for _ in range(n):
            val = (val << 1) | self.read_bit()
        return val

    def close(self):
        self.file.close()


# ==========================
# RICE DECODE
# ==========================

def rice_decode_escape(reader, k):

    threshold = max(8, min(16, k + 4))
    flag = reader.read_bit()

    if flag == 0:
        # NORMAL MODE
        q = 0
        while True:
            bit = reader.read_bit()
            if bit == 0:
                break
            q += 1

        r = reader.read_bits(k) if k > 0 else 0
        return (q << k) | r

    else:
        # ESCAPE MODE
        return reader.read_bits(BPP + 4)


# ==========================
# IO
# ==========================

def load_hex(filename):
    print("Loading HEX:", filename)
    with open(filename) as f:
        data = [int(line.strip(), 16) for line in f]
    return np.array(data, dtype=np.int32).reshape((HEIGHT, WIDTH))


def save_hex(img, filename):
    with open(filename, "w") as f:
        for val in img.flatten():
            f.write(f"{val:02X}\n")


# ==========================
# DECODE ONLY
# ==========================

def decode_only(binfile):

    reader = BitReader(binfile)
    recon = np.zeros((HEIGHT, WIDTH), dtype=np.int32)

    A_est = 4
    k = msb_pos(A_est)

    for y in range(HEIGHT):
        for x in range(WIDTH):

            A = recon[y, x-1] if x > 0 else 0
            B = recon[y-1, x] if y > 0 else 0
            C = recon[y-1, x-1] if (x > 0 and y > 0) else 0

            X_hat = med_predict(A, B, C)

            U = rice_decode_escape(reader, k)
            E = unsigned_to_signed(U)

            recon[y, x] = max(0, min(255, X_hat + E))

            A_est = max(1, A_est + ((U - A_est) >> S))
            k = msb_pos(A_est)

    reader.close()
    return recon


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    print("=====================================")
    print("DECODE + VERIFY")
    print("=====================================")

    # Load original (reference)
    original = load_hex(INPUT_HEX)

    # Decode compressed
    print("\nDecoding...")
    recon = decode_only(INPUT_BIN)

    # Save reconstructed
    save_hex(recon, RECON_HEX)

    # ==========================
    # VERIFICATION
    # ==========================
    print("\nVerification")
    print("---------------------")

    match = np.array_equal(original, recon)

    if match:
        print("✅ PERFECT RECONSTRUCTION")
    else:
        print("❌ MISMATCH DETECTED")

        # find first mismatch (VERY useful for debugging RTL)
        diff = np.where(original != recon)
        y, x = diff[0][0], diff[1][0]

        print(f"First mismatch at (y={y}, x={x})")
        print(f"Original     = {original[y,x]}")
        print(f"Reconstructed= {recon[y,x]}")

    print("=====================================")