import os
import base64
import io
import json
import math
import numpy as np
import cv2
from flask import send_from_directory
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Untuk mengizinkan request dari frontend React

# ─────────────────────────────────────────────────────────────
# NOTE: Decode base64 → OpenCV image (BGR numpy array)
# ─────────────────────────────────────────────────────────────
def decode_image(b64_string: str) -> np.ndarray:
    header, data = b64_string.split(",", 1)
    img_bytes = base64.b64decode(data)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img

# ─────────────────────────────────────────────────────────────
# NOTE: OpenCV image → base64 PNG string
# ─────────────────────────────────────────────────────────────
def encode_image(img: np.ndarray) -> str:
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise ValueError("Gagal encode gambar")
    b64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{b64}"

# ─────────────────────────────────────────────────────────────
# NOTE: Ambil sample matriks piksel (grayscale) ukuran n×n
# ─────────────────────────────────────────────────────────────
def get_pixel_matrix(img: np.ndarray, n: int = 5, start_row: int = 0, start_col: int = 0) -> list:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape
    r = min(start_row + n, h)
    c = min(start_col + n, w)
    patch = gray[start_row:r, start_col:c]
    return patch.tolist()

# ─────────────────────────────────────────────────────────────
# NOTE: Histogram grayscale
# ─────────────────────────────────────────────────────────────
def get_histogram(img: np.ndarray) -> list:
    try:
        # Pastikan gambar dalam format uint8
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)

        # Ubah ke grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Hitung histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        hist_list = []
        for val in hist:
            v = float(val[0])
            hist_list.append(0.0 if math.isnan(v) else v)
            
        return hist_list
    except Exception as e:
        print(f"Error Histogram: {e}")
        return [0.0] * 256 

# ─────────────────────────────────────────────────────────────
# OPERASI 1: Info Dasar + Grayscale
# ─────────────────────────────────────────────────────────────
def op_grayscale(img: np.ndarray, params: dict) -> dict:
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)  # agar tetap 3 channel untuk encode

    pixel_matrix = get_pixel_matrix(img, n=5)
    gray_matrix  = get_pixel_matrix(result, n=5)

    # Ambil 1 piksel contoh untuk penjelasan
    b, g, r_ = int(img[0,0,0]), int(img[0,0,1]), int(img[0,0,2])
    lum = round(0.299*r_ + 0.587*g + 0.114*b, 2)

    explanation = {
        "title": "Konversi Grayscale",
        "formula": r"L = 0.299R + 0.587G + 0.114B",
        "description": (
            "Setiap piksel RGB dikonversi menjadi satu nilai luminance (kecerahan). "
            "Bobot berbeda karena mata manusia lebih sensitif terhadap hijau."
        ),
        "pixel_before": pixel_matrix,
        "pixel_after": gray_matrix,
        "steps": [
            f"Piksel sudut kiri atas: R={r_}, G={g}, B={b}",
            f"L = 0.299×{r_} + 0.587×{g} + 0.114×{b}",
            f"L = {round(0.299*r_,3)} + {round(0.587*g,3)} + {round(0.114*b,3)}",
            f"L = {lum} ≈ {int(lum)}",
        ],
        "image_info": {
            "width": w,
            "height": h,
            "mode": "BGR → Grayscale",
            "size_kb": round(w * h * 3 / 1024, 1),
        },
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 2: Image Blending (α·A + (1−α)·B)
# ─────────────────────────────────────────────────────────────
def op_blending(img: np.ndarray, params: dict) -> dict:
    alpha = float(params.get("alpha", 0.5))
    b64_second = params.get("second_image", "")

    if b64_second:
        img2 = decode_image(b64_second)
        img2 = cv2.resize(img2, (img.shape[1], img.shape[0]))
    else:
        img2 = cv2.GaussianBlur(img, (31, 31), 0)

    result = cv2.addWeighted(img, alpha, img2, 1 - alpha, 0)

    p1 = img[0, 0].tolist()
    p2 = img2[0, 0].tolist()
    p_out = [round(alpha * a + (1 - alpha) * b) for a, b in zip(p1, p2)]

    explanation = {
        "title": "Image Blending",
        "formula": r"g(x,y) = \alpha \cdot f_1(x,y) + (1-\alpha) \cdot f_2(x,y)",
        "description": (
            f"Dua gambar digabungkan dengan bobot α={alpha} untuk gambar pertama "
            f"dan (1-α)={(1-alpha):.2f} untuk gambar kedua."
        ),
        "steps": [
            f"α = {alpha}, 1-α = {1-alpha:.2f}",
            f"Piksel [0,0] gambar 1: BGR={p1}",
            f"Piksel [0,0] gambar 2: BGR={p2}",
            f"Output = {alpha}×{p1} + {1-alpha:.2f}×{p2}",
            f"Output ≈ {p_out}",
        ],
        "kernel": None,
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 3: Background Subtraction
# ─────────────────────────────────────────────────────────────
def op_subtraction(img: np.ndarray, params: dict) -> dict:
    blur = cv2.GaussianBlur(img, (51, 51), 0)
    diff = cv2.absdiff(img, blur)
    result = cv2.convertScaleAbs(diff * 3)

    p1 = img[10, 10].tolist()
    p2 = blur[10, 10].tolist()
    p_out = [abs(int(a) - int(b)) for a, b in zip(p1, p2)]

    explanation = {
        "title": "Background Subtraction",
        "formula": r"D(x,y) = |f(x,y) - B(x,y)|",
        "description": (
            "Gambar background (blur berat) dikurangi dari gambar asli untuk menonjolkan foreground."
        ),
        "steps": [
            "Background B(x,y) = GaussianBlur(f, 51×51)",
            f"Piksel asli [10,10]: {p1}",
            f"Piksel background [10,10]: {p2}",
            f"D = |{p1} - {p2}| = {p_out}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 4: Rotasi
# ─────────────────────────────────────────────────────────────
def op_rotation(img: np.ndarray, params: dict) -> dict:
    angle = float(params.get("angle", 45))
    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2
    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    result = cv2.warpAffine(img, M, (w, h))

    rad = math.radians(angle)
    explanation = {
        "title": "Rotasi",
        "formula": r"\begin{pmatrix}x'\\y'\end{pmatrix}=\begin{pmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{pmatrix}\begin{pmatrix}x-c_x\\y-c_y\end{pmatrix}+\begin{pmatrix}c_x\\c_y\end{pmatrix}",
        "description": f"Gambar dirotasi {angle}° terhadap titik pusat ({cx}, {cy}).",
        "steps": [
            f"θ = {angle}°, cos θ = {round(math.cos(rad),4)}, sin θ = {round(math.sin(rad),4)}",
            f"Pusat rotasi: ({cx}, {cy})",
            f"Piksel (100, 50): x-cx={100-cx}, y-cy={50-cy}",
            f"x' = cos({angle}°)·{100-cx} + (-sin({angle}°))·{50-cy} + {cx}",
            f"x' ≈ {round(math.cos(rad)*(100-cx) - math.sin(rad)*(50-cy) + cx, 1)}",
        ],
        "matrix": M.tolist(),
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 5: Scaling
# ─────────────────────────────────────────────────────────────
def op_scaling(img: np.ndarray, params: dict) -> dict:
    sx = float(params.get("sx", 1.5))
    sy = float(params.get("sy", 1.5))
    h, w = img.shape[:2]
    new_w, new_h = int(w * sx), int(h * sy)
    result = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    explanation = {
        "title": "Scaling (Resize)",
        "formula": r"\begin{pmatrix}x'\\y'\end{pmatrix}=\begin{pmatrix}s_x&0\\0&s_y\end{pmatrix}\begin{pmatrix}x\\y\end{pmatrix}",
        "description": f"Gambar diperbesar/diperkecil dengan faktor sx={sx}, sy={sy}.",
        "steps": [
            f"Ukuran asli: {w}×{h} piksel",
            f"Faktor: sx={sx}, sy={sy}",
            f"Ukuran baru: {new_w}×{new_h} piksel",
            f"Piksel (10, 10) → ({int(10*sx)}, {int(10*sy)})",
            "Interpolasi bilinear digunakan untuk mengisi piksel baru.",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 6: Translasi
# ─────────────────────────────────────────────────────────────
def op_translation(img: np.ndarray, params: dict) -> dict:
    tx = int(params.get("tx", 50))
    ty = int(params.get("ty", 50))
    h, w = img.shape[:2]
    M = np.float32([[1, 0, tx], [0, 1, ty]])
    result = cv2.warpAffine(img, M, (w, h))

    explanation = {
        "title": "Translasi",
        "formula": r"\begin{pmatrix}x'\\y'\end{pmatrix}=\begin{pmatrix}x\\y\end{pmatrix}+\begin{pmatrix}t_x\\t_y\end{pmatrix}",
        "description": f"Gambar digeser sejauh tx={tx} piksel ke kanan dan ty={ty} piksel ke bawah.",
        "steps": [
            f"tx = {tx}, ty = {ty}",
            f"Piksel (50, 30) → ({50+tx}, {30+ty})",
            "Matriks transformasi afin:",
            f"M = [[1, 0, {tx}], [0, 1, {ty}]]",
        ],
        "matrix": M.tolist(),
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 7: Flip
# ─────────────────────────────────────────────────────────────
def op_flip(img: np.ndarray, params: dict) -> dict:
    mode = params.get("mode", "horizontal")
    flip_code = 1 if mode == "horizontal" else 0 if mode == "vertical" else -1
    result = cv2.flip(img, flip_code)

    h, w = img.shape[:2]
    if mode == "horizontal":
        formula = r"f'(x,y) = f(W-1-x, y)"
        step = f"Piksel (10, 20) → ({w-1-10}, 20)"
    elif mode == "vertical":
        formula = r"f'(x,y) = f(x, H-1-y)"
        step = f"Piksel (10, 20) → (10, {h-1-20})"
    else:
        formula = r"f'(x,y) = f(W-1-x, H-1-y)"
        step = f"Piksel (10, 20) → ({w-1-10}, {h-1-20})"

    explanation = {
        "title": f"Flip {mode.capitalize()}",
        "formula": formula,
        "description": f"Gambar dicerminkan secara {mode}.",
        "steps": [
            f"Mode: {mode}",
            f"Dimensi: {w}×{h}",
            step,
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 8: Brightness
# ─────────────────────────────────────────────────────────────
def op_brightness(img: np.ndarray, params: dict) -> dict:
    beta = int(params.get("beta", 50))
    result = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)

    p = int(img[0, 0, 0])
    p_out = min(255, max(0, p + beta))

    explanation = {
        "title": "Penyesuaian Kecerahan (Brightness)",
        "formula": r"g(x,y) = f(x,y) + \beta",
        "description": f"Nilai β={beta} ditambahkan ke setiap piksel. Nilai diklem pada [0, 255].",
        "steps": [
            f"β = {beta}",
            f"Piksel asli [0,0] channel B: {p}",
            f"g = {p} + {beta} = {p + beta}",
            f"Setelah clamping: g = {p_out}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 9: Contrast
# ─────────────────────────────────────────────────────────────
def op_contrast(img: np.ndarray, params: dict) -> dict:
    alpha = float(params.get("alpha", 1.5))
    result = cv2.convertScaleAbs(img, alpha=alpha, beta=0)

    p = int(img[0, 0, 0])
    p_out = min(255, max(0, int(alpha * p)))

    explanation = {
        "title": "Penyesuaian Kontras",
        "formula": r"g(x,y) = \alpha \cdot f(x,y)",
        "description": (
            f"Setiap piksel dikalikan faktor α={alpha}. "
            "α>1 meningkatkan kontras, α<1 mengurangi kontras."
        ),
        "steps": [
            f"α = {alpha}",
            f"Piksel asli [0,0] channel B: {p}",
            f"g = {alpha} × {p} = {round(alpha * p, 2)}",
            f"Setelah clamping: g = {p_out}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 10: Negative
# ─────────────────────────────────────────────────────────────
def op_negative(img: np.ndarray, params: dict) -> dict:
    result = cv2.bitwise_not(img)

    p = int(img[0, 0, 0])
    p_out = 255 - p

    explanation = {
        "title": "Citra Negatif",
        "formula": r"g(x,y) = 255 - f(x,y)",
        "description": "Setiap nilai piksel diinvers. Piksel terang menjadi gelap dan sebaliknya.",
        "steps": [
            f"Piksel asli [0,0] channel B: {p}",
            f"g = 255 - {p} = {p_out}",
            "Operasi ini membalik seluruh histogram citra.",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 11: Thresholding
# ─────────────────────────────────────────────────────────────
def op_thresholding(img: np.ndarray, params: dict) -> dict:
    thresh_val = int(params.get("threshold", 128))
    mode = params.get("mode", "binary")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if mode == "binary":
        _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
        formula = r"g(x,y) = \begin{cases} 255 & \text{jika } f(x,y) \geq T \\ 0 & \text{sebaliknya} \end{cases}"
    elif mode == "otsu":
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        formula = r"T^* = \arg\max_T [\sigma_B^2(T)]"
    else:
        _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
        formula = r"g(x,y) = \begin{cases} 0 & \text{jika } f(x,y) \geq T \\ 255 & \text{sebaliknya} \end{cases}"

    result = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

    p = int(gray[0, 0])
    p_out = 255 if p >= thresh_val else 0

    explanation = {
        "title": f"Thresholding ({mode})",
        "formula": formula,
        "description": f"Piksel diubah menjadi hitam atau putih berdasarkan threshold T={thresh_val}.",
        "steps": [
            f"T = {thresh_val}, mode = {mode}",
            f"Piksel grayscale [0,0]: {p}",
            f"{p} {'≥' if p >= thresh_val else '<'} {thresh_val}  → output = {p_out}",
        ],
        "pixel_before": get_pixel_matrix(gray),
        "pixel_after": get_pixel_matrix(thresh),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 12: Mean Filter
# ─────────────────────────────────────────────────────────────
def op_mean_filter(img: np.ndarray, params: dict) -> dict:
    ksize = int(params.get("ksize", 3))
    if ksize % 2 == 0:
        ksize += 1  # harus ganjil
    result = cv2.blur(img, (ksize, ksize))

    kernel_val = round(1 / (ksize * ksize), 4)
    kernel = [[kernel_val] * ksize for _ in range(ksize)]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    patch = get_pixel_matrix(gray, n=ksize)

    # Hitung output piksel tengah secara manual
    flat = [gray[i, j] for i in range(ksize) for j in range(ksize)]
    manual_out = round(sum(flat) / len(flat), 2)

    explanation = {
        "title": f"Mean Filter ({ksize}×{ksize})",
        "formula": r"g(x,y) = \frac{1}{k^2}\sum_{m=-k/2}^{k/2}\sum_{n=-k/2}^{k/2} f(x+m, y+n)",
        "description": (
            f"Setiap piksel digantikan rata-rata dari {ksize}×{ksize} = {ksize*ksize} tetangganya. "
            "Digunakan untuk smoothing / mengurangi noise."
        ),
        "kernel": kernel,
        "steps": [
            f"Kernel: {ksize}×{ksize}, bobot = 1/{ksize*ksize} = {kernel_val}",
            f"Patch piksel {ksize}×{ksize} dari pojok kiri atas:",
            str(patch),
            f"Rata-rata = {sum(flat)}/{ksize*ksize} = {manual_out}",
        ],
        "pixel_before": patch,
        "pixel_after": get_pixel_matrix(result, n=ksize),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 13: Median Filter
# ─────────────────────────────────────────────────────────────
def op_median_filter(img: np.ndarray, params: dict) -> dict:
    ksize = int(params.get("ksize", 3))
    if ksize % 2 == 0:
        ksize += 1
    result = cv2.medianBlur(img, ksize)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    patch = get_pixel_matrix(gray, n=ksize)
    flat = sorted([gray[i, j] for i in range(ksize) for j in range(ksize)])
    median_val = flat[len(flat) // 2]

    explanation = {
        "title": f"Median Filter ({ksize}×{ksize})",
        "formula": r"g(x,y) = \text{median}\{f(x+m, y+n) \;|\; m,n \in W\}",
        "description": (
            f"Setiap piksel digantikan nilai median dari {ksize}×{ksize} tetangganya. "
            "Sangat efektif menghilangkan salt-and-pepper noise."
        ),
        "kernel": None,
        "steps": [
            f"Kumpulkan {ksize}×{ksize} = {ksize*ksize} piksel tetangga",
            f"Nilai-nilai: {flat}",
            f"Diurutkan → nilai ke-{len(flat)//2 + 1} = {median_val}",
            f"Output piksel = {median_val}",
        ],
        "pixel_before": patch,
        "pixel_after": get_pixel_matrix(result, n=ksize),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 14: Sobel Edge Detection
# ─────────────────────────────────────────────────────────────
def op_sobel(img: np.ndarray, params: dict) -> dict:
    direction = params.get("direction", "both")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.GaussianBlur(gray, (3, 3), 0)

    sobelx = cv2.Sobel(gray_blur, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray_blur, cv2.CV_64F, 0, 1, ksize=3)

    if direction == "x":
        magnitude = cv2.convertScaleAbs(sobelx)
        formula = r"G_x = \begin{pmatrix}-1&0&1\\-2&0&2\\-1&0&1\end{pmatrix} * f"
        kernel = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    elif direction == "y":
        magnitude = cv2.convertScaleAbs(sobely)
        formula = r"G_y = \begin{pmatrix}-1&-2&-1\\0&0&0\\1&2&1\end{pmatrix} * f"
        kernel = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
    else:
        magnitude = cv2.magnitude(sobelx, sobely)
        magnitude = np.clip(magnitude, 0, 255).astype(np.uint8)
        formula = r"G = \sqrt{G_x^2 + G_y^2}"
        kernel = None  # keduanya digunakan

    result = cv2.cvtColor(magnitude, cv2.COLOR_GRAY2BGR)

    patch = get_pixel_matrix(gray, n=3)
    kx = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    # Konvolusi manual untuk pojok kiri atas (padding dengan 0)
    flat_gray = [[int(gray[r, c]) if r < gray.shape[0] and c < gray.shape[1] else 0 for c in range(3)] for r in range(3)]
    gx_manual = sum(kx[r][c] * flat_gray[r][c] for r in range(3) for c in range(3))

    explanation = {
        "title": f"Sobel Edge Detection ({direction})",
        "formula": formula,
        "description": (
            "Sobel menggunakan konvolusi kernel 3×3 untuk mendeteksi gradien intensitas. "
            f"Tepi {'horizontal' if direction=='y' else 'vertikal' if direction=='x' else 'semua arah'} akan ditonjolkan."
        ),
        "kernel": kernel if kernel else [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
        "steps": [
            "Kernel Sobel-X:",
            str(kx),
            f"Patch piksel 3×3 (grayscale):\n{flat_gray}",
            f"Gx = Σ(kernel × piksel) = {gx_manual}",
            "Magnitude = √(Gx² + Gy²)",
        ],
        "pixel_before": patch,
        "pixel_after": get_pixel_matrix(magnitude if len(magnitude.shape) == 2 else cv2.cvtColor(magnitude, cv2.COLOR_BGR2GRAY), n=3),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 15: Studi Kasus - Full Enhancement Pipeline
# ─────────────────────────────────────────────────────────────
def op_enhance_pipeline(img: np.ndarray, params: dict) -> dict:
    brightness = int(params.get("beta", 30))
    contrast   = float(params.get("alpha", 1.3))

    # Step 1: Brightness
    step1 = cv2.convertScaleAbs(img, alpha=1.0, beta=brightness)
    # Step 2: Contrast
    step2 = cv2.convertScaleAbs(step1, alpha=contrast, beta=0)
    # Step 3: Unsharp masking (sharpening)
    blur = cv2.GaussianBlur(step2, (0, 0), 3)
    step3 = cv2.addWeighted(step2, 1.5, blur, -0.5, 0)
    # Step 4: Median denoising
    result = cv2.medianBlur(step3, 3)

    explanation = {
        "title": "Studi Kasus: Enhancement Pipeline",
        "formula": r"g = \text{MedianFilter}(\text{Sharpen}(\alpha \cdot (f + \beta)))",
        "description": (
            "Pipeline pengolahan citra untuk meningkatkan kualitas foto gelap: "
            "Brightness → Contrast → Sharpening → Denoising."
        ),
        "steps": [
            f"1. Brightness: g₁ = f + {brightness}",
            f"2. Contrast:   g₂ = {contrast} × g₁",
            "3. Sharpening: g₃ = 1.5×g₂ − 0.5×GaussianBlur(g₂)",
            "4. Denoising:  g₄ = MedianFilter(g₃, 3×3)",
        ],
        "pipeline": [
            {"name": "Original", "beta": 0, "alpha": 1.0},
            {"name": "+Brightness", "beta": brightness, "alpha": 1.0},
            {"name": "+Contrast", "beta": brightness, "alpha": contrast},
            {"name": "+Sharpen+Denoise", "beta": brightness, "alpha": contrast},
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),

        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }
    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 16: Multiplication
# ─────────────────────────────────────────────────────────────
def op_multiplication(img: np.ndarray, params: dict) -> dict:
    b64_second = params.get("second_image", "")

    if b64_second:
        img2 = decode_image(b64_second)
        img2 = cv2.resize(img2, (img.shape[1], img.shape[0]))
    else:
        img2 = cv2.GaussianBlur(img, (31, 31), 0)

    result = cv2.multiply(img, img2, scale=1/255.0)

    explanation = {
        "title": "Image Multiplication",
        "formula": r"g(x,y) = \frac{f_1(x,y) \times f_2(x,y)}{255}",
        "description": "Mengalikan dua citra. Karena diskalakan (/255), gambar akan cenderung lebih gelap. Sangat berguna untuk efek Masking.",
        "steps": [
            "Nilai piksel f1 dikalikan f2.",
            "Hasilnya dibagi 255 untuk mencegah overflow (keterangan berlebih).",
            "Piksel hitam (0) pada gambar kedua akan membuat area tersebut jadi hitam total."
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }

    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# OPERASI 17: Division
# ─────────────────────────────────────────────────────────────
def op_division(img: np.ndarray, params: dict) -> dict:
    b64_second = params.get("second_image", "")

    if b64_second:
        img2 = decode_image(b64_second)
        img2 = cv2.resize(img2, (img.shape[1], img.shape[0]))
    else:
        img2 = cv2.GaussianBlur(img, (31, 31), 0)

    img2[img2 == 0] = 1

    result = cv2.divide(img, img2, scale=255.0)

    explanation = {
        "title": "Image Division",
        "formula": r"g(x,y) = \frac{f_1(x,y)}{f_2(x,y)} \times 255",
        "description": "Membagi citra pertama dengan citra kedua. Karena diskalakan (x255), hasilnya akan menerangkan gambar. Sering dipakai untuk perbaikan bayangan (Shading Correction).",
        "steps": [
            "Piksel bernilai 0 pada gambar kedua diubah jadi 1 agar tidak error.",
            "Nilai piksel f1 dibagi f2.",
            "Hasilnya dikalikan 255 agar kembali ke rentang normal.",
            "Piksel yang gelap akibat bayangan bisa menjadi normal kembali."
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }

    return {"result": result, "explanation": explanation}

# ─────────────────────────────────────────────────────────────
# ROUTER: mapping nama operasi → fungsi
# ─────────────────────────────────────────────────────────────
OPERATIONS = {
    "grayscale":        op_grayscale,
    "blending":         op_blending,
    "subtraction":      op_subtraction,
    "multiply":         op_multiplication,
    "divide":           op_division,
    "rotation":         op_rotation,
    "scaling":          op_scaling,
    "translation":      op_translation,
    "flip":             op_flip,
    "brightness":       op_brightness,
    "contrast":         op_contrast,
    "negative":         op_negative,
    "thresholding":     op_thresholding,
    "mean_filter":      op_mean_filter,
    "median_filter":    op_median_filter,
    "sobel":            op_sobel,
    "enhance_pipeline": op_enhance_pipeline,
}

# ─────────────────────────────────────────────────────────────
# ROUTE UTAMA: POST /api/process
# ─────────────────────────────────────────────────────────────
@app.route("/api/process", methods=["POST"])
def process_image():
    try:
        data       = request.get_json()
        operation  = data.get("operation", "grayscale")
        params     = data.get("params", {})
        image_b64  = data.get("image")

        if not image_b64:
            return jsonify({"error": "Tidak ada gambar yang dikirim"}), 400
        if operation not in OPERATIONS:
            return jsonify({"error": f"Operasi '{operation}' tidak dikenal"}), 400

        img = decode_image(image_b64)
        fn  = OPERATIONS[operation]
        out = fn(img, params)

        return jsonify({
            "before":      image_b64,
            "after":       encode_image(out["result"]),
            "explanation": out["explanation"],
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

# ─────────────────────────────────────────────────────────────
# ROUTE: GET /api/operations  (daftar operasi yang tersedia)
# ─────────────────────────────────────────────────────────────
@app.route("/api/operations", methods=["GET"])
def list_operations():
    return jsonify({"operations": list(OPERATIONS.keys())})

# ─────────────────────────────────────────────────────────────
# ROUTE: Health check
# ─────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})

@app.route("/")
def serve():
    return send_from_directory("../frontend/dist", "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    file_path = os.path.join("../frontend/dist", path)

    if os.path.exists(file_path):
        return send_from_directory("../frontend/dist", path)
    else:
        return send_from_directory("../frontend/dist", "index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

