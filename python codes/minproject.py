import numpy as np
import cv2
import os
import struct
from tkinter import Tk, filedialog


# ============================================================
# SAFE MED PREDICTOR
# ============================================================

def med_predict(a, b, c):
    a, b, c = int(a), int(b), int(c)

    if c >= max(a, b):
        return min(a, b)
    elif c <= min(a, b):
        return max(a, b)
    else:
        return a + b - c


def predictive_encode(img):
    h, w = img.shape
    err = np.zeros((h, w), dtype=np.int16)

    for i in range(h):
        for j in range(w):
            a = img[i, j-1] if j > 0 else 0
            b = img[i-1, j] if i > 0 else 0
            c = img[i-1, j-1] if (i > 0 and j > 0) else 0

            pred = med_predict(a, b, c)
            err[i, j] = int(img[i, j]) - pred

    return err


def predictive_decode(err):
    h, w = err.shape
    img = np.zeros((h, w), dtype=np.int16)

    for i in range(h):
        for j in range(w):
            a = img[i, j-1] if j > 0 else 0
            b = img[i-1, j] if i > 0 else 0
            c = img[i-1, j-1] if (i > 0 and j > 0) else 0

            pred = med_predict(a, b, c)
            img[i, j] = int(err[i, j]) + pred

    return img


# ============================================================
# ZIGZAG SIGN MAPPING
# ============================================================

def signed_to_unsigned(v):
    return v * 2 if v >= 0 else -2 * v - 1


def unsigned_to_signed(u):
    return u // 2 if (u & 1) == 0 else -(u // 2) - 1


# ============================================================
# BITSTREAM CLASSES
# ============================================================

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


# ============================================================
# RICE ENCODE / DECODE WITH ESC SYMBOL
# ============================================================

def rice_encode_value(u, bw, k):
    q = u >> k
    r = u & ((1 << k) - 1)

    for _ in range(q):
        bw.write_bit(0)
    bw.write_bit(1)

    if k > 0:
        bw.write_bits(r, k)


def rice_decode_value(br, k):
    q = 0
    while br.read_bit() == 0:
        q += 1

    r = br.read_bits(k) if k > 0 else 0
    return (q << k) | r


def choose_k(block):
    mean = np.mean(np.abs(block))
    if mean < 1: return 0
    if mean < 2: return 1
    if mean < 4: return 2
    if mean < 8: return 3
    if mean < 16: return 4
    return 5


# ✅ ESCAPE SYMBOL METHOD (NO MODE BIT)

def rice_escape_encode(err, bw, T=7, block=16):
    ESC = T + 1
    escape_count = 0

    h, w = err.shape

    for i in range(0, h, block):
        for j in range(0, w, block):

            blk = err[i:i+block, j:j+block]
            k = choose_k(blk)

            bw.write_bits(k, 3)

            for v in blk.flatten():
                v = int(v)

                if abs(v) <= T:
                    u = signed_to_unsigned(v)
                    rice_encode_value(u, bw, k)

                else:
                    escape_count += 1

                    # Encode ESC marker
                    u_esc = signed_to_unsigned(ESC)
                    rice_encode_value(u_esc, bw, k)

                    # Store full residual raw after marker (9 bits)
                    raw = v & 0x1FF
                    bw.write_bits(raw, 9)

    return escape_count


def rice_escape_decode(br, shape, T=7, block=16):
    ESC = T + 1
    h, w = shape
    err = np.zeros((h, w), dtype=np.int16)

    for i in range(0, h, block):
        for j in range(0, w, block):

            bh = min(block, h - i)
            bw2 = min(block, w - j)

            k = br.read_bits(3)

            for y in range(bh):
                for x in range(bw2):

                    u = rice_decode_value(br, k)
                    v = unsigned_to_signed(u)

                    if v == ESC:
                        # Escape → read raw residual
                        raw = br.read_bits(9)
                        if raw >= 256:
                            raw -= 512
                        err[i+y, j+x] = raw
                    else:
                        err[i+y, j+x] = v

    return err


# ============================================================
# MAIN
# ============================================================

def main():
    Tk().withdraw()
    path = filedialog.askopenfilename(title="Select Grayscale Image")

    if not path:
        return

    name = os.path.splitext(os.path.basename(path))[0]
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    if gray is None:
        print("Load PNG/JPG only.")
        return

    h, w = gray.shape
    N = h * w

    print("\n[1] Encoding...")
    err = predictive_encode(gray)

    bw = BitWriter()
    escapes = rice_escape_encode(err, bw, T=7)
    bitstream = bw.flush()

    residual_file = f"{name}_RES_ESC.bin"
    with open(residual_file, "wb") as f:
        f.write(struct.pack("II", h, w))
        f.write(bitstream)

    print("[2] Decoding...")
    with open(residual_file, "rb") as f:
        hh, ww = struct.unpack("II", f.read(8))
        data = f.read()

    br = BitReader(data)
    decErr = rice_escape_decode(br, (hh, ww), T=7)

    rec = predictive_decode(decErr)
    rec = np.clip(rec, 0, 255).astype(np.uint8)

    rec_file = f"{name}_REC.png"
    cv2.imwrite(rec_file, rec)

    # Size report
    s_png = os.path.getsize(path)
    s_res = os.path.getsize(residual_file)

    bpp = (s_res * 8) / N
    perfect = np.array_equal(gray, rec)

    print("\n" + "=" * 70)
    print("✅ RESERVED ESCAPE SYMBOL RESULTS")
    print("=" * 70)
    print(f"PNG Size            : {s_png/1024:.2f} KB")
    print(f"Residual Size       : {s_res/1024:.2f} KB")
    print(f"Bits Per Pixel      : {bpp:.4f}")
    print(f"Escape Count        : {escapes}")
    print(f"Pixel Perfect       : {perfect}")
    print("=" * 70)


if __name__ == "__main__":
    main()