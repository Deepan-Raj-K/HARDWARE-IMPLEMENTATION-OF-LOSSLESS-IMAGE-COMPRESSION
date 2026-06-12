import sys, os, math, struct
import numpy as np
from PIL import Image
import cv2
import rawpy

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QGridLayout, QGroupBox, QFileDialog, QVBoxLayout
)

################################################################################
# RAW / IMAGE LOADER
################################################################################

def load_raw_as_8bit(path):
    ext = os.path.splitext(path)[1].lower()

    if ext in [".dng", ".nef", ".cr2", ".arw", ".rw2"]:
        with rawpy.imread(path) as raw:
            rgb16 = raw.postprocess(
                use_camera_wb=True,
                half_size=False,
                no_auto_bright=True,
                gamma=(1,1),
                output_bps=16
            )
        # Convert 16-bit → 8-bit
        rgb8 = (rgb16 / 256).astype(np.uint8)
        return cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR), "RAW"

    img = Image.open(path).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR), "RGB"


def to_pixmap(img, w=360, h=240):
    img_small = cv2.resize(img, (w, h))
    h_, w_, ch = img_small.shape
    bytes_per_line = w_ * ch
    qimg = QImage(img_small.data, w_, h_, bytes_per_line, QImage.Format_BGR888)
    return QPixmap.fromImage(qimg)


################################################################################
# ENCODER — RAW → JPEG + Residual PNG → .JXR
################################################################################

def encode_jxr(rgb8, jpeg_img, residual, output_path):
    jpg_bytes = cv2.imencode(".jpg", cv2.cvtColor(jpeg_img, cv2.COLOR_BGR2RGB))[1].tobytes()

    vis = np.clip(residual + 128, 0, 255).astype(np.uint8)
    vis_bgr = cv2.cvtColor(vis, cv2.COLOR_RGB2BGR)
    png_bytes = cv2.imencode(".png", vis_bgr)[1].tobytes()

    with open(output_path, "wb") as f:
        f.write(struct.pack("<II", len(jpg_bytes), len(png_bytes)))
        f.write(jpg_bytes)
        f.write(png_bytes)


################################################################################
# DECODER — .JXR → RAW reconstructed
################################################################################

def decode_jxr(jxr_path):
    data = open(jxr_path, "rb").read()

    jpeg_len, png_len = struct.unpack("<II", data[:8])
    jpeg_data = data[8:8+jpeg_len]
    png_data = data[8+jpeg_len:8+jpeg_len+png_len]

    jpg_arr = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
    jpeg = cv2.cvtColor(jpg_arr, cv2.COLOR_BGR2RGB)

    vis_arr = cv2.imdecode(np.frombuffer(png_data, np.uint8), cv2.IMREAD_COLOR)
    vis_rgb = cv2.cvtColor(vis_arr, cv2.COLOR_BGR2RGB)

    residual = vis_rgb.astype(np.int16) - 128

    reconstructed = np.clip(jpeg.astype(np.int16) + residual, 0, 255).astype(np.uint8)

    return reconstructed


################################################################################
# GUI APPLICATION
################################################################################

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAW → JXR Encoder/Decoder — v3.0 (8-bit corrected)")

        self.raw_8bit = None
        self.jpeg_img = None
        self.residual = None

        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout(self)

        g_load = QGroupBox("Load RAW Image")
        gl = QVBoxLayout()
        self.path_edit = QLineEdit()
        b_browse = QPushButton("Browse")
        b_browse.clicked.connect(self.on_browse)
        b_load = QPushButton("Load 8-bit RAW")
        b_load.clicked.connect(self.on_load)
        gl.addWidget(self.path_edit)
        gl.addWidget(b_browse)
        gl.addWidget(b_load)
        g_load.setLayout(gl)

        g_proc = QGroupBox("Processing")
        gp = QVBoxLayout()

        b_jpeg = QPushButton("1️⃣ JPEG Convert")
        b_jpeg.clicked.connect(self.on_jpeg)

        b_res = QPushButton("2️⃣ Residual Compute")
        b_res.clicked.connect(self.on_residual)

        b_enc = QPushButton("3️⃣ Encode JXR")
        b_enc.clicked.connect(self.on_encode_jxr)

        b_dec = QPushButton("4️⃣ Decode JXR")
        b_dec.clicked.connect(self.on_decode_jxr)

        gp.addWidget(b_jpeg)
        gp.addWidget(b_res)
        gp.addWidget(b_enc)
        gp.addWidget(b_dec)
        g_proc.setLayout(gp)

        self.lbl_raw = QLabel("RAW 8-bit")
        self.lbl_raw.setAlignment(Qt.AlignCenter)

        self.lbl_jpeg = QLabel("JPEG")
        self.lbl_jpeg.setAlignment(Qt.AlignCenter)

        self.lbl_res = QLabel("Residual")
        self.lbl_res.setAlignment(Qt.AlignCenter)

        self.lbl_rec = QLabel("Reconstructed")
        self.lbl_rec.setAlignment(Qt.AlignCenter)

        self.lbl_info = QLabel("")
        self.lbl_info.setAlignment(Qt.AlignLeft)

        layout.addWidget(g_load, 0, 0)
        layout.addWidget(g_proc, 1, 0)
        layout.addWidget(self.lbl_raw, 0, 1)
        layout.addWidget(self.lbl_jpeg, 1, 1)
        layout.addWidget(self.lbl_res, 0, 2)
        layout.addWidget(self.lbl_rec, 1, 2)
        layout.addWidget(self.lbl_info, 2, 0, 1, 3)


    # -------------------------------------------------------------------------
    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose RAW file")
        if path:
            self.path_edit.setText(path)

    def on_load(self):
        path = self.path_edit.text().strip()
        self.raw_8bit, _ = load_raw_as_8bit(path)
        self.preview(self.lbl_raw, self.raw_8bit)
        self.lbl_info.setText("RAW loaded → converted to 8-bit")

    def on_jpeg(self):
        jpeg_path = os.path.join(self.output_dir, "jpeg.jpg")
        Image.fromarray(cv2.cvtColor(self.raw_8bit, cv2.COLOR_BGR2RGB)).save(jpeg_path, "JPEG", quality=80)

        self.jpeg_img = np.array(Image.open(jpeg_path).convert("RGB"))
        self.jpeg_img = cv2.cvtColor(self.jpeg_img, cv2.COLOR_RGB2BGR)

        self.preview(self.lbl_jpeg, self.jpeg_img)

    def on_residual(self):
        raw_rgb = cv2.cvtColor(self.raw_8bit, cv2.COLOR_BGR2RGB)
        jpg_rgb = cv2.cvtColor(self.jpeg_img, cv2.COLOR_BGR2RGB)

        self.residual = raw_rgb.astype(np.int16) - jpg_rgb.astype(np.int16)

        vis = np.clip(self.residual + 128, 0, 255).astype(np.uint8)
        vis_bgr = cv2.cvtColor(vis, cv2.COLOR_RGB2BGR)

        self.preview(self.lbl_res, vis_bgr)
        self.lbl_info.setText("Residual created")

    def on_encode_jxr(self):
        out = os.path.join(self.output_dir, "container.jxr")
        encode_jxr(self.raw_8bit, self.jpeg_img, self.residual, out)
        self.lbl_info.setText("JXR encoded")

    def on_decode_jxr(self):
        path = os.path.join(self.output_dir, "container.jxr")
        rec = decode_jxr(path)
        rec_bgr = cv2.cvtColor(rec, cv2.COLOR_RGB2BGR)
        self.preview(self.lbl_rec, rec_bgr)
        self.lbl_info.setText("JXR decoded → reconstructed")

    def preview(self, label, img):
        pix = to_pixmap(img, 360, 240)
        label.setPixmap(pix)


def main():
    app = QApplication(sys.argv)
    w = App()
    w.resize(1400, 600)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()