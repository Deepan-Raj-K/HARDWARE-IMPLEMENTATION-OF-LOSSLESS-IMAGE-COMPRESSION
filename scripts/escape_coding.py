import numpy as np
import os

# ==========================
# USER PARAMETERS
# ==========================
WIDTH  = 512
HEIGHT = 512
BPP = 8
S = 4

INPUT_HEX  = "F:/Documents/Academics/mini project/pre and post processing/misc/top10/img12.hex"
OUTPUT_BIN = "compressed_noise.bin"
RECON_HEX  = "reconstructed_noisy_bmp.hex"


# ==========================
# UTILS
# ==========================

def msb_pos(val):
    if val <= 0:
        return 0
    return int(np.floor(np.log2(val)))

def signed_to_unsigned(e):
    return 2*e if e >= 0 else -2*e - 1

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
# BIT IO
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
# FLAG-BASED ESCAPE CODING
# ==========================

def rice_encode_escape(writer, value, k):

    q = value >> k
    threshold = max(8, min(16, k + 4))

    if q < threshold:
        # FLAG = 0 → NORMAL MODE
        writer.write_bit(0)

        # Unary q
        for _ in range(q):
            writer.write_bit(1)
        writer.write_bit(0)

        # Remainder
        if k > 0:
            writer.write_bits(value & ((1 << k) - 1), k)

    else:
        # FLAG = 1 → ESCAPE MODE
        writer.write_bit(1)

        # Write full value
        writer.write_bits(value, BPP + 4)


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
    print("Loading HEX file...")
    with open(filename) as f:
        data = [int(line.strip(), 16) for line in f]

    img = np.array(data, dtype=np.int32).reshape((HEIGHT, WIDTH))
    print("Loaded", len(data), "pixels")
    return img


def save_hex(img, filename):
    with open(filename, "w") as f:
        for val in img.flatten():
            f.write(f"{val:02X}\n")


# ==========================
# ENCODE
# ==========================

def encode(img, outfile):

    writer = BitWriter(outfile)
    recon = np.zeros_like(img)

    A_est = 4
    k = msb_pos(A_est)

    for y in range(HEIGHT):
        for x in range(WIDTH):

            X = img[y, x]

            A = recon[y, x-1] if x > 0 else 0
            B = recon[y-1, x] if y > 0 else 0
            C = recon[y-1, x-1] if (x > 0 and y > 0) else 0

            X_hat = med_predict(A, B, C)

            E = X - X_hat
            U = signed_to_unsigned(E)

            rice_encode_escape(writer, U, k)

            recon[y, x] = max(0, min(255, X_hat + E))

            A_est = max(1, A_est + ((U - A_est) >> S))
            k = msb_pos(A_est)

    writer.close()
    return writer.total_bits


# ==========================
# DECODE
# ==========================

def decode(binfile):

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
    print("HEX → Compression (FLAG-BASED ESCAPE)")
    print("=====================================")

    img = load_hex(INPUT_HEX)

    compressed_bits = encode(img, OUTPUT_BIN)
    compressed_bytes = os.path.getsize(OUTPUT_BIN)

    original_bits = img.size * BPP

    print("\nCompression Results")
    print("---------------------")
    print("Image Resolution:", WIDTH, "x", HEIGHT)
    print("Original bits:", original_bits)
    print("Compressed bits:", compressed_bits)
    print("Compressed bytes:", compressed_bytes)
    print("Compression ratio:", original_bits / compressed_bits)
    print("Bits per pixel:", compressed_bits / img.size)

    print("\nDecoding...")
    recon = decode(OUTPUT_BIN)

    save_hex(recon, RECON_HEX)

    print("\nLossless Verification")
    print("---------------------")
    print("Lossless:", np.array_equal(img, recon))

    print("=====================================")