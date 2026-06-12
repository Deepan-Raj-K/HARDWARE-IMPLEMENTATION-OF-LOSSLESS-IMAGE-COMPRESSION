import numpy as np
import os

# ==========================
# USER PARAMETERS
# ==========================
WIDTH  = 256
HEIGHT = 256
BPP = 8
S = 4

INPUT_HEX  = "F:\Documents\Academics\mini project\pre and post processing\dataset\img8.hex"
OUTPUT_BIN = "compressed_noise.bin"


# ==========================
# UTILITY FUNCTIONS
# ==========================

def msb_pos(val):
    if val <= 0:
        return 0
    return int(np.floor(np.log2(val)))


def signed_to_unsigned(e):
    return 2*e if e >= 0 else -2*e - 1


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


# ==========================
# HEX IMAGE LOADER
# ==========================

def load_hex_image(filename):

    print("Loading HEX file...")

    with open(filename, "r") as f:
        data = [int(line.strip(), 16) for line in f]

    img = np.array(data, dtype=np.int32)

    if len(img) != WIDTH * HEIGHT:
        raise ValueError("HEX file size does not match expected resolution")

    img = img.reshape((HEIGHT, WIDTH))

    print("Loaded", len(data), "pixels")

    return img


# ==========================
# ENCODER
# ==========================

def encode(image, binfile):

    h, w = image.shape

    writer = BitWriter(binfile)

    recon = np.zeros((h, w), dtype=np.int32)

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

            pixel = X_hat + E
            pixel = max(0, min((1 << BPP)-1, pixel))

            recon[y, x] = pixel

            diff = U - A_est
            A_est = max(1, A_est + (diff >> S))
            k = msb_pos(A_est)

    writer.close()

    return writer.total_bits


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    print("=====================================")
    print("HEX → Compression Pipeline")
    print("=====================================")

    img = load_hex_image(INPUT_HEX)

    compressed_bits = encode(img, OUTPUT_BIN)

    compressed_bytes = os.path.getsize(OUTPUT_BIN)

    original_bits = img.size * BPP

    ratio = original_bits / compressed_bits
    bpp = compressed_bits / img.size

    print("\nCompression Results")
    print("---------------------")
    print("Image Resolution:", WIDTH, "x", HEIGHT)
    print("Original bits:", original_bits)
    print("Compressed bits:", compressed_bits)
    print("Compressed size (bytes):", compressed_bytes)
    print("Compression ratio:", ratio)
    print("Bits per pixel:", bpp)

    print("\nCompressed BIN saved as:", OUTPUT_BIN)
    print("=====================================")