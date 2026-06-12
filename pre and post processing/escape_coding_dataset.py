import numpy as np
import os
from PIL import Image

# ==========================
# USER PARAMETERS
# ==========================
BPP = 8
S = 4

INPUT_FOLDER = r"F:\Documents\Academics\mini project\pre and post processing\misc\misc"


# ==========================
# UTILS
# ==========================

def msb_pos(val):
    val = int(val)  # FIX: convert numpy → python int
    return val.bit_length() - 1 if val > 0 else 0


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
# RICE ENCODE
# ==========================

def rice_encode_escape(writer, value, k):

    q = value >> k
    threshold = max(8, min(16, k + 4))

    if q < threshold:
        writer.write_bit(0)

        for _ in range(q):
            writer.write_bit(1)
        writer.write_bit(0)

        if k > 0:
            writer.write_bits(value & ((1 << k) - 1), k)

    else:
        writer.write_bit(1)
        writer.write_bits(value, BPP + 4)


# ==========================
# LOAD HEX
# ==========================

def load_hex(filename, width, height):
    with open(filename) as f:
        data = [int(line.strip(), 16) for line in f]

    if len(data) != width * height:
        raise ValueError(f"Size mismatch: HEX={len(data)}, TIFF={width*height}")

    return np.array(data, dtype=np.int32).reshape((height, width))


# ==========================
# ENCODE
# ==========================

def encode(img, outfile, width, height):

    writer = BitWriter(outfile)
    recon = np.zeros((height, width), dtype=np.int32)

    A_est = 4
    k = msb_pos(A_est)

    for y in range(height):
        for x in range(width):

            X = int(img[y, x])

            A = int(recon[y, x-1]) if x > 0 else 0
            B = int(recon[y-1, x]) if y > 0 else 0
            C = int(recon[y-1, x-1]) if (x > 0 and y > 0) else 0

            X_hat = med_predict(A, B, C)

            E = X - X_hat

            # Inline (faster)
            if E >= 0:
                U = E << 1
            else:
                U = (-E << 1) - 1

            rice_encode_escape(writer, U, k)

            recon[y, x] = max(0, min(255, X_hat + E))

            A_est = int(max(1, A_est + ((U - A_est) >> S)))  # keep int
            k = msb_pos(A_est)

    writer.close()
    return writer.total_bits


# ==========================
# MAIN LOOP
# ==========================

if __name__ == "__main__":

    print("=====================================")
    print("Batch HEX → BIN Compression Started")
    print("=====================================")

    for file in sorted(os.listdir(INPUT_FOLDER)):

        if file.endswith(".hex"):
            hex_path = os.path.join(INPUT_FOLDER, file)
            base_name = os.path.splitext(file)[0]

            # Match TIFF
            tiff_path = os.path.join(INPUT_FOLDER, base_name + ".tiff")

            if not os.path.exists(tiff_path):
                print(f"[SKIP] No TIFF for {file}")
                continue

            try:
                # Get dimensions
                with Image.open(tiff_path) as img_ref:
                    width, height = img_ref.size

                print(f"\nProcessing: {file}")
                print(f"Resolution: {width} x {height}")

                # Load HEX
                img = load_hex(hex_path, width, height)

                # Output BIN
                bin_path = os.path.join(INPUT_FOLDER, base_name + ".bin")

                # Encode
                compressed_bits = encode(img, bin_path, width, height)
                compressed_bytes = os.path.getsize(bin_path)

                original_bits = img.size * BPP

                print("Compressed bytes :", compressed_bytes)
                print("Compression ratio:", original_bits / compressed_bits)
                print("Bits per pixel   :", compressed_bits / img.size)

            except Exception as e:
                print(f"[ERROR] {file}: {e}")

    print("\n=====================================")
    print("Batch Processing Completed!")
    print("=====================================")