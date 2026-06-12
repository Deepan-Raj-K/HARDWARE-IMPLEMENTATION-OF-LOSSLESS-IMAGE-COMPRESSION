import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ==============================
# GLOBAL STATE
# ==============================
img_array = None
comp_bytes = None

# ==============================
# FUNCTIONS
# ==============================

def load_image():
    global img_array

    path = filedialog.askopenfilename(filetypes=[
        ("Images", "*.png *.jpg *.jpeg *.bmp")
    ])

    if not path:
        return

    img = Image.open(path).convert("L")
    img_array = np.array(img)

    # Resize for display
    img_disp = img.resize((300, 250))
    img_tk = ImageTk.PhotoImage(img_disp)

    image_label.config(image=img_tk)
    image_label.image = img_tk

    show_histogram()
    update_metrics()


def show_histogram():
    global img_array

    for widget in hist_frame.winfo_children():
        widget.destroy()

    fig, ax = plt.subplots(figsize=(4,2))
    ax.hist(img_array.ravel(), bins=64)
    ax.set_title("Histogram")

    canvas = FigureCanvasTkAgg(fig, master=hist_frame)
    canvas.draw()
    canvas.get_tk_widget().pack()


def run_compression():
    global img_array, comp_bytes

    if img_array is None:
        status_label.config(text="Load image first!", fg="red")
        return

    pixels = img_array.size

    # Simulated compression
    comp_bytes = int(pixels * 0.6)

    status_label.config(text="Compression Done!", fg="green")

    update_metrics()


def update_metrics():
    global img_array, comp_bytes

    if img_array is None:
        return

    pixels = img_array.size
    orig_bytes = pixels

    if comp_bytes is None:
        comp = orig_bytes
    else:
        comp = comp_bytes

    ratio = orig_bytes / comp
    bpp = (comp * 8) / pixels

    res_label.config(text=f"{img_array.shape[1]} x {img_array.shape[0]}")
    orig_label.config(text=f"{orig_bytes/1024:.2f} KB")
    comp_label.config(text=f"{comp/1024:.2f} KB")
    ratio_label.config(text=f"{ratio:.2f}x")
    bpp_label.config(text=f"{bpp:.2f}")


# ==============================
# GUI LAYOUT
# ==============================

root = tk.Tk()
root.title("MEDRICE - Image Compression Workbench")
root.geometry("900x600")
root.configure(bg="#0b0f14")

# Title
title = tk.Label(root, text="MEDRICE Workbench",
                 fg="#00e5a0", bg="#0b0f14",
                 font=("Consolas", 18, "bold"))
title.pack(pady=10)

# ==============================
# TOP FRAME (IMAGE + HIST)
# ==============================
top_frame = tk.Frame(root, bg="#0b0f14")
top_frame.pack(pady=10)

# Image display
image_label = tk.Label(top_frame, bg="#1c2534", width=300, height=250)
image_label.grid(row=0, column=0, padx=20)

# Histogram frame
hist_frame = tk.Frame(top_frame, bg="#1c2534", width=300, height=250)
hist_frame.grid(row=0, column=1, padx=20)

# ==============================
# BUTTONS
# ==============================
btn_frame = tk.Frame(root, bg="#0b0f14")
btn_frame.pack(pady=10)

load_btn = tk.Button(btn_frame, text="Load Image", command=load_image,
                     bg="#3d9cff", fg="white", width=15)
load_btn.grid(row=0, column=0, padx=10)

run_btn = tk.Button(btn_frame, text="START Compression", command=run_compression,
                    bg="#00e5a0", fg="black", width=20)
run_btn.grid(row=0, column=1, padx=10)

status_label = tk.Label(root, text="Idle", bg="#0b0f14", fg="#6b7f99")
status_label.pack()

# ==============================
# METRICS PANEL
# ==============================
metrics_frame = tk.Frame(root, bg="#141a22")
metrics_frame.pack(pady=15, fill="x", padx=20)

def create_tile(parent, label_text):
    frame = tk.Frame(parent, bg="#1c2534", padx=10, pady=5)
    title = tk.Label(frame, text=label_text, fg="#6b7f99", bg="#1c2534")
    value = tk.Label(frame, text="—", fg="#00e5a0",
                     bg="#1c2534", font=("Consolas", 12, "bold"))
    title.pack()
    value.pack()
    return frame, value

tiles = []
labels = ["Resolution", "Original Size", "Compressed Size", "Ratio", "BPP"]
value_labels = []

for i, name in enumerate(labels):
    tile, val = create_tile(metrics_frame, name)
    tile.grid(row=0, column=i, padx=10)
    value_labels.append(val)

res_label, orig_label, comp_label, ratio_label, bpp_label = value_labels

# ==============================
# RUN APP
# ==============================
root.mainloop()