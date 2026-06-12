import numpy as np
import rawpy
import cv2
from tkinter import Tk, filedialog

# ==============================
# Select DNG File
# ==============================

Tk().withdraw()
file_path = filedialog.askopenfilename(
    title="Select DNG Image",
    filetypes=[("DNG files", "*.dng")]
)

print("Loading DNG...")

with rawpy.imread(file_path) as raw:
    rgb_image = raw.postprocess(output_bps=16)

rgb_image = rgb_image.astype(np.int32)

height, width, channels = rgb_image.shape
total_pixels = height * width * channels

print("Image dtype:", rgb_image.dtype)
print("Max value:", rgb_image.max())

# ==============================
# Save original 16-bit RGB PNG
# ==============================

cv2.imwrite(
    "original_rgb.png",
    cv2.cvtColor(rgb_image.astype(np.uint16), cv2.COLOR_RGB2BGR)
)

# ==============================
# MED Predictor
# ==============================

def predict_pixel(img, i, j, c):
    if i == 0 and j == 0:
        return 0
    elif i == 0:
        return img[i, j-1, c]
    elif j == 0:
        return img[i-1, j, c]

    A = img[i, j-1, c]
    B = img[i-1, j, c]
    C = img[i-1, j-1, c]

    if C >= max(A, B):
        return min(A, B)
    elif C <= min(A, B):
        return max(A, B)
    else:
        return A + B - C

# ==============================
# Signed ↔ Unsigned Mapping
# ==============================

def signed_to_unsigned(x):
    return 2*x if x >= 0 else -2*x - 1

def unsigned_to_signed(x):
    return x//2 if x % 2 == 0 else -(x//2) - 1

# ==============================
# Rice Encode
# ==============================

def rice_encode(value, k):
    q = value >> k
    r = value & ((1 << k) - 1)
    return '1'*q + '0' + format(r, f'0{k}b')

# ==============================
# Safe Rice Decode
# ==============================

def rice_decode(bitstream, idx, k, limit):
    q = 0

    while idx < limit and bitstream[idx] == '1':
        q += 1
        idx += 1

    if idx >= limit:
        return 0, idx

    idx += 1  # skip zero

    if k > 0:
        if idx + k > limit:
            return 0, idx
        r = int(bitstream[idx:idx+k], 2)
        idx += k
    else:
        r = 0

    return (q << k) + r, idx

# ==============================
# Adaptive Block Rice Encoding (FAST)
# ==============================

block_size = 32
bitstream_parts = []

print("Encoding...")

for c in range(3):

    for bi in range(0, height, block_size):
        for bj in range(0, width, block_size):

            errors = []

            for i in range(bi, min(bi+block_size, height)):
                for j in range(bj, min(bj+block_size, width)):

                    pred = predict_pixel(rgb_image, i, j, c)
                    error = rgb_image[i, j, c] - pred
                    errors.append(signed_to_unsigned(error))

            mean_val = np.mean(errors)
            k = max(0, min(15, int(np.log2(mean_val + 1)))) if mean_val > 0 else 0

            # 4-bit header for k
            bitstream_parts.append(format(k, '04b'))

            for val in errors:
                bitstream_parts.append(rice_encode(val, k))

# Join once (FAST)
bitstream = ''.join(bitstream_parts)
original_bit_length = len(bitstream)

# ==============================
# Save Compressed File
# ==============================

print("Saving compressed file...")

padding = (8 - len(bitstream) % 8) % 8
bitstream += '0' * padding

byte_data = bytearray()
for i in range(0, len(bitstream), 8):
    byte_data.append(int(bitstream[i:i+8], 2))

with open("compressed.bin", "wb") as f:
    f.write(byte_data)

compressed_size = len(byte_data) / (1024*1024)
original_size = rgb_image.nbytes / (1024*1024)

# ==============================
# Decoding
# ==============================

print("Decoding...")

reconstructed = np.zeros_like(rgb_image)
idx = 0
limit = original_bit_length

for c in range(3):

    for bi in range(0, height, block_size):
        for bj in range(0, width, block_size):

            if idx + 4 > limit:
                break

            k = int(bitstream[idx:idx+4], 2)
            idx += 4

            for i in range(bi, min(bi+block_size, height)):
                for j in range(bj, min(bj+block_size, width)):

                    if idx >= limit:
                        break

                    value, idx = rice_decode(bitstream, idx, k, limit)
                    error = unsigned_to_signed(value)

                    pred = predict_pixel(reconstructed, i, j, c)
                    reconstructed[i, j, c] = pred + error

# Convert to uint16
reconstructed = reconstructed.astype(np.uint16)

# ==============================
# Save Reconstructed 16-bit RGB
# ==============================

cv2.imwrite(
    "reconstructed_rgb.png",
    cv2.cvtColor(reconstructed, cv2.COLOR_RGB2BGR)
)

# ==============================
# Results
# ==============================

bpp = original_bit_length / total_pixels

print("\nResults:")
print("Compressed size:", compressed_size, "MB")
print("Original size:", original_size, "MB")
print("Bits per pixel:", bpp)
print("Lossless match:", np.array_equal(rgb_image.astype(np.uint16), reconstructed))
