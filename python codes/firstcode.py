import sys, os, math
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

def load_any(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in [".dng", ".nef", ".cr2", ".arw", ".rw2"]:
        with rawpy.imread(path) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                half_size=False,
                no_auto_bright=True,
                gamma=(1,1),
            )
        return rgb, "RAW"
    else:
        img = Image.open(path).convert("RGB")
        return np.array(img), "RGB"


def to_pixmap(img, w=360, h=240):
    img_small = cv2.resize(img, (w, h))
    h_, w_, ch = img_small.shape
    bytes_per_line = w_ * ch
    qimg = QImage(img_small.data, w_, h_, bytes_per_line, QImage.Format_BGR888)
    return QPixmap.fromImage(qimg)


################################################################################
# GUI APPLICATION
################################################################################

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAW → JPEG → Residual → Reconstruct — v1.0")

        self.raw_img = None
        self.jpeg_img = None
        self.residual = None
        self.reconstructed = None
        self.raw_path = None
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

        self._build_ui()

    # -------------------------------------------------------------------------
    # UI DESIGN
    # -------------------------------------------------------------------------
    def _build_ui(self):
        layout = QGridLayout(self)

        # -------- INPUT PANEL --------
        g_load = QGroupBox("Load RAW Image")
        gl = QVBoxLayout()
        self.path_edit = QLineEdit()
        b_browse = QPushButton("Browse Image")
        b_browse.clicked.connect(self.on_browse)
        b_load = QPushButton("Load")
        b_load.clicked.connect(self.on_load)
        gl.addWidget(self.path_edit)
        gl.addWidget(b_browse)
        gl.addWidget(b_load)
        g_load.setLayout(gl)

        # -------- PROCESS PANEL --------
        g_proc = QGroupBox("Processing")
        gp = QVBoxLayout()
        b_jpeg = QPushButton("1️⃣ Create JPEG")
        b_jpeg.clicked.connect(self.on_jpeg)
        b_res = QPushButton("2️⃣ Compute Residual")
        b_res.clicked.connect(self.on_residual)
        b_rec = QPushButton("3️⃣ Reconstruct")
        b_rec.clicked.connect(self.on_reconstruct)
        gp.addWidget(b_jpeg)
        gp.addWidget(b_res)
        gp.addWidget(b_rec)
        g_proc.setLayout(gp)

        # -------- DISPLAY PANELS --------
        self.lbl_raw = QLabel("RAW preview")
        self.lbl_raw.setAlignment(Qt.AlignCenter)

        self.lbl_jpeg = QLabel("JPEG preview")
        self.lbl_jpeg.setAlignment(Qt.AlignCenter)

        self.lbl_res = QLabel("Residual preview")
        self.lbl_res.setAlignment(Qt.AlignCenter)

        self.lbl_rec = QLabel("Reconstructed preview")
        self.lbl_rec.setAlignment(Qt.AlignCenter)

        # -------- INFO AREA --------
        self.lbl_info = QLabel("")
        self.lbl_info.setAlignment(Qt.AlignLeft)

        # -------- LAYOUT SETUP --------
        layout.addWidget(g_load,       0, 0)
        layout.addWidget(g_proc,       1, 0)
        layout.addWidget(self.lbl_raw, 0, 1)
        layout.addWidget(self.lbl_jpeg,1, 1)
        layout.addWidget(self.lbl_res, 0, 2)
        layout.addWidget(self.lbl_rec, 1, 2)
        layout.addWidget(self.lbl_info,2, 0, 1, 3)


    # -------------------------------------------------------------------------
    # BUTTON LOGIC
    # -------------------------------------------------------------------------
    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose image")
        if path:
            self.path_edit.setText(path)

    def on_load(self):
        try:
            self.raw_path = self.path_edit.text().strip()
            img, fmt = load_any(self.raw_path)
            self.raw_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            self.preview(self.lbl_raw, self.raw_img)
            self.lbl_info.setText("RAW loaded successfully")
        except Exception as e:
            self.lbl_info.setText(f"ERROR: {e}")

    def on_jpeg(self):
        if self.raw_img is None:
            self.lbl_info.setText("Load RAW first")
            return

        jpeg_path = os.path.join(self.output_dir, "jpeg.jpg")
        im = Image.fromarray(cv2.cvtColor(self.raw_img, cv2.COLOR_BGR2RGB))
        im.save(jpeg_path, "JPEG", quality=80)
        self.jpeg_img = np.array(Image.open(jpeg_path))

        self.jpeg_img = cv2.cvtColor(self.jpeg_img, cv2.COLOR_RGB2BGR)
        self.preview(self.lbl_jpeg, self.jpeg_img)
        self.lbl_info.setText("JPEG created")

    def on_residual(self):
        if self.jpeg_img is None:
            self.lbl_info.setText("Create JPEG first")
            return

        raw_rgb = cv2.cvtColor(self.raw_img, cv2.COLOR_BGR2RGB)
        jpg_rgb = cv2.cvtColor(self.jpeg_img, cv2.COLOR_BGR2RGB)

        self.residual = raw_rgb.astype(np.int16) - jpg_rgb.astype(np.int16)

        vis = np.clip(self.residual + 128, 0, 255).astype(np.uint8)
        vis_bgr = cv2.cvtColor(vis, cv2.COLOR_RGB2BGR)

        self.preview(self.lbl_res, vis_bgr)
        np.save(os.path.join(self.output_dir, "residual.npy"), self.residual)

        self.lbl_info.setText("Residual computed and saved")

    def on_reconstruct(self):
        if self.residual is None:
            self.lbl_info.setText("Compute residual first")
            return

        jpg_rgb = cv2.cvtColor(self.jpeg_img, cv2.COLOR_BGR2RGB)

        self.reconstructed = np.clip(jpg_rgb.astype(np.int16) + self.residual, 0, 255).astype(np.uint8)
        rec_bgr = cv2.cvtColor(self.reconstructed, cv2.COLOR_RGB2BGR)

        Image.fromarray(self.reconstructed).save(os.path.join(self.output_dir, "reconstructed.png"))
        self.preview(self.lbl_rec, rec_bgr)

        self.compute_stats()

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------
    def compute_stats(self):
        raw_rgb = cv2.cvtColor(self.raw_img, cv2.COLOR_BGR2RGB)
        rms = np.sqrt(np.mean(self.residual**2))
        mse = np.mean((raw_rgb.astype(np.float32) - self.reconstructed.astype(np.float32))**2)
        psnr = float("inf") if mse == 0 else 20 * math.log10(255.0 / math.sqrt(mse))

        raw_size = os.path.getsize(self.raw_path)
        jpeg_size = os.path.getsize(os.path.join(self.output_dir, "jpeg.jpg"))
        res_size = self.residual.nbytes

        self.lbl_info.setText(
            f"RMS: {rms:.3f}\n"
            f"PSNR: {psnr:.2f} dB\n"
            f"RAW: {raw_size/1024:.1f} KB\n"
            f"JPEG: {jpeg_size/1024:.1f} KB\n"
            f"Residual: {res_size/1024:.1f} KB\n"
            f"Total: {(jpeg_size + res_size)/1024:.1f} KB"
        )

    # -------------------------------------------------------------------------
    # IMAGE PREVIEW
    # -------------------------------------------------------------------------
    def preview(self, label, img):
        pix = to_pixmap(img, 360, 240)
        label.setPixmap(pix)


################################################################################
# RUN
################################################################################

def main():
    app = QApplication(sys.argv)
    w = App()
    w.resize(1400, 600)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()