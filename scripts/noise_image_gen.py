import numpy as np
import cv2

def add_salt_pepper_noise(image, prob):

    noisy = image.copy()

    # Random matrix [0,1]
    rand = np.random.rand(*image.shape)

    # Salt (white pixels)
    noisy[rand < prob/2] = 255

    # Pepper (black pixels)
    noisy[rand > 1 - prob/2] = 0

    return noisy


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    # Load grayscale image
    img = cv2.imread("F:\Documents\Academics\mini project\pre and post processing\dataset\img7_gray.bmp", cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise ValueError("Image not found")

    # Noise probability (tune this)
    prob = 0.02   # 2% noise

    noisy_img = add_salt_pepper_noise(img, prob)

    # Save result
    cv2.imwrite("F:\Documents\Academics\mini project\pre and post processing\dataset\\nimg7_gray.bmp", noisy_img)

    print("Noisy image saved as noisy_bmp.bmp")