import os, base64, math
import numpy as np
import cv2
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def decode_image(b64: str) -> np.ndarray:
    _, data = b64.split(",", 1)
    arr = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Gambar tidak valid")
    return img

def encode_image(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Gagal encode")
    return "data:image/png;base64," + base64.b64encode(buf).decode()

def encode_rgba(img: np.ndarray) -> str:
    """Encode BGRA (4-channel) image as PNG with transparency"""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Gagal encode RGBA")
    return "data:image/png;base64," + base64.b64encode(buf).decode()

def get_pixel_matrix(img: np.ndarray, n=5, r0=0, c0=0) -> list:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
    h, w = gray.shape
    return gray[r0:min(r0+n,h), c0:min(c0+n,w)].tolist()

def get_histogram(img: np.ndarray) -> list:
    try:
        img = img.astype(np.uint8) if img.dtype != np.uint8 else img
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
        hist = cv2.calcHist([gray],[0],None,[256],[0,256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        return [float(v[0]) if math.isfinite(float(v[0])) else 0.0 for v in hist]
    except:
        return [0.0]*256

def op_grayscale(img, params):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    b, g, r_ = int(img[0,0,0]), int(img[0,0,1]), int(img[0,0,2])
    lum = round(0.299*r_ + 0.587*g + 0.114*b, 2)
    return {"result": result, "explanation": {
        "title": "Konversi Grayscale",
        "formula": r"L = 0.299R + 0.587G + 0.114B",
        "description": "Setiap piksel RGB → satu nilai luminance. Bobot berbeda karena mata manusia lebih sensitif terhadap hijau.",
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "steps": [f"R={r_}, G={g}, B={b}", f"L = 0.299×{r_} + 0.587×{g} + 0.114×{b} = {lum} ≈ {int(lum)}"],
        "image_info": {"width": w, "height": h, "mode": "BGR→Grayscale", "size_kb": round(w*h*3/1024,1)},
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_blending(img, params):
    alpha = float(params.get("alpha", 0.5))
    b64s = params.get("second_image","")
    img2 = decode_image(b64s) if b64s else cv2.GaussianBlur(img,(31,31),0)
    img2 = cv2.resize(img2,(img.shape[1],img.shape[0]))
    result = cv2.addWeighted(img, alpha, img2, 1-alpha, 0)
    p1, p2 = img[0,0].tolist(), img2[0,0].tolist()
    return {"result": result, "explanation": {
        "title": "Image Blending",
        "formula": r"g(x,y) = \alpha \cdot f_1(x,y) + (1-\alpha) \cdot f_2(x,y)",
        "description": f"Dua gambar digabungkan dengan α={alpha} dan (1-α)={(1-alpha):.2f}.",
        "steps": [f"α={alpha}", f"Piksel img1[0,0]: {p1}", f"Piksel img2[0,0]: {p2}", f"Output ≈ {[round(alpha*a+(1-alpha)*b) for a,b in zip(p1,p2)]}"],
        "kernel": None, "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_subtraction(img, params):
    blur = cv2.GaussianBlur(img,(51,51),0)
    result = cv2.convertScaleAbs(cv2.absdiff(img,blur)*3)
    p1, p2 = img[10,10].tolist(), blur[10,10].tolist()
    return {"result": result, "explanation": {
        "title": "Background Subtraction",
        "formula": r"D(x,y) = |f(x,y) - B(x,y)|",
        "description": "Background (Gaussian blur 51×51) dikurangi dari gambar asli.",
        "steps": ["B(x,y) = GaussianBlur(f, 51×51)", f"Piksel asli[10,10]: {p1}", f"Background[10,10]: {p2}", f"D = {[abs(int(a)-int(b)) for a,b in zip(p1,p2)]}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_multiplication(img, params):
    b64s = params.get("second_image","")
    img2 = decode_image(b64s) if b64s else cv2.GaussianBlur(img,(31,31),0)
    img2 = cv2.resize(img2,(img.shape[1],img.shape[0]))
    result = cv2.multiply(img, img2, scale=1/255.0)
    return {"result": result, "explanation": {
        "title": "Image Multiplication",
        "formula": r"g(x,y) = \frac{f_1(x,y) \times f_2(x,y)}{255}",
        "description": "Perkalian piksel dua gambar, dibagi 255 agar hasilnya kembali ke rentang [0,255]. Berguna untuk masking.",
        "steps": ["Nilai piksel f1 × f2", "Dibagi 255 untuk mencegah overflow", "Piksel hitam di img2 → area jadi hitam total"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_division(img, params):
    b64s = params.get("second_image","")
    img2 = decode_image(b64s) if b64s else cv2.GaussianBlur(img,(31,31),0)
    img2 = cv2.resize(img2,(img.shape[1],img.shape[0]))
    img2[img2==0] = 1
    result = cv2.divide(img, img2, scale=255.0)
    return {"result": result, "explanation": {
        "title": "Image Division",
        "formula": r"g(x,y) = \frac{f_1(x,y)}{f_2(x,y)} \times 255",
        "description": "Pembagian piksel dua gambar. Berguna untuk Shading Correction (koreksi pencahayaan tidak merata).",
        "steps": ["Piksel 0 di img2 → diganti 1 agar tidak error (ZeroDivision)", "f1 ÷ f2 × 255", "Area gelap akibat bayangan bisa kembali normal"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_rotation(img, params):
    angle = float(params.get("angle",45))
    h, w = img.shape[:2]; cx, cy = w//2, h//2
    M = cv2.getRotationMatrix2D((cx,cy), angle, 1.0)
    result = cv2.warpAffine(img, M, (w,h))
    rad = math.radians(angle)
    return {"result": result, "explanation": {
        "title": "Rotasi",
        "formula": r"\begin{pmatrix}x'\\y'\end{pmatrix}=\begin{pmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{pmatrix}\begin{pmatrix}x-c_x\\y-c_y\end{pmatrix}+\begin{pmatrix}c_x\\c_y\end{pmatrix}",
        "description": f"Rotasi {angle}° terhadap pusat ({cx},{cy}).",
        "steps": [f"θ={angle}°, cosθ={round(math.cos(rad),4)}, sinθ={round(math.sin(rad),4)}", f"Pusat: ({cx},{cy})"],
        "matrix": M.tolist(), "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_scaling(img, params):
    sx=float(params.get("sx",1.5)); sy=float(params.get("sy",1.5))
    h,w=img.shape[:2]; nw,nh=int(w*sx),int(h*sy)
    result=cv2.resize(img,(nw,nh),interpolation=cv2.INTER_LINEAR)
    return {"result": result, "explanation": {
        "title": "Scaling (Resize)",
        "formula": r"\begin{pmatrix}x'\\y'\end{pmatrix}=\begin{pmatrix}s_x&0\\0&s_y\end{pmatrix}\begin{pmatrix}x\\y\end{pmatrix}",
        "description": f"Resize dengan sx={sx}, sy={sy}.",
        "steps": [f"Asli: {w}×{h}", f"Baru: {nw}×{nh}", "Interpolasi bilinear untuk mengisi piksel."],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_translation(img, params):
    tx=int(params.get("tx",50)); ty=int(params.get("ty",50))
    h,w=img.shape[:2]; M=np.float32([[1,0,tx],[0,1,ty]])
    result=cv2.warpAffine(img,M,(w,h))
    return {"result": result, "explanation": {
        "title": "Translasi",
        "formula": r"\begin{pmatrix}x'\\y'\end{pmatrix}=\begin{pmatrix}x\\y\end{pmatrix}+\begin{pmatrix}t_x\\t_y\end{pmatrix}",
        "description": f"Geser tx={tx}px kanan, ty={ty}px bawah.",
        "steps": [f"M = [[1,0,{tx}],[0,1,{ty}]]", f"Piksel (50,30) → ({50+tx},{30+ty})"],
        "matrix": M.tolist(), "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_flip(img, params):
    mode=params.get("mode","horizontal")
    fc=1 if mode=="horizontal" else 0 if mode=="vertical" else -1
    result=cv2.flip(img,fc); h,w=img.shape[:2]
    fm={"horizontal":r"f'(x,y)=f(W-1-x,y)","vertical":r"f'(x,y)=f(x,H-1-y)","both":r"f'(x,y)=f(W-1-x,H-1-y)"}
    return {"result": result, "explanation": {
        "title": f"Flip {mode.capitalize()}",
        "formula": fm[mode], "description": f"Cerminkan secara {mode}.",
        "steps": [f"mode={mode}, flip_code={fc}", f"W={w},H={h}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_brightness(img, params):
    beta=int(params.get("beta",50)); result=cv2.convertScaleAbs(img,alpha=1.0,beta=beta)
    p=int(img[0,0,0]); po=min(255,max(0,p+beta))
    return {"result": result, "explanation": {
        "title": "Brightness (Kecerahan)",
        "formula": r"g(x,y) = \text{clip}(f(x,y) + \beta,\;0,\;255)",
        "description": f"β={beta} ditambahkan ke setiap piksel.",
        "steps": [f"β={beta}", f"Piksel[0,0]B: {p}", f"g={p}+{beta}={p+beta}", f"Clip→{po}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_contrast(img, params):
    alpha=float(params.get("alpha",1.5)); result=cv2.convertScaleAbs(img,alpha=alpha,beta=0)
    p=int(img[0,0,0]); po=min(255,max(0,int(alpha*p)))
    return {"result": result, "explanation": {
        "title": "Contrast (Kontras)",
        "formula": r"g(x,y) = \text{clip}(\alpha \cdot f(x,y),\;0,\;255)",
        "description": f"α={alpha}. α>1 meningkatkan, α<1 mengurangi kontras.",
        "steps": [f"α={alpha}", f"Piksel[0,0]B: {p}", f"g={alpha}×{p}={round(alpha*p,2)}", f"Clip→{po}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_negative(img, params):
    result=cv2.bitwise_not(img); p=int(img[0,0,0])
    return {"result": result, "explanation": {
        "title": "Citra Negatif",
        "formula": r"g(x,y) = 255 - f(x,y)",
        "description": "Inversi semua piksel. Terang jadi gelap dan sebaliknya.",
        "steps": [f"Piksel[0,0]B: {p}", f"g=255-{p}={255-p}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_thresholding(img, params):
    tv=int(params.get("threshold",128)); mode=params.get("mode","binary")
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    if mode=="binary": _,thresh=cv2.threshold(gray,tv,255,cv2.THRESH_BINARY); fml=r"g=255 \text{ jika } f\geq T,\; 0 \text{ sebaliknya}"
    elif mode=="otsu": _,thresh=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU); fml=r"T^*=\arg\max_T[\sigma_B^2(T)]"
    else: _,thresh=cv2.threshold(gray,tv,255,cv2.THRESH_BINARY_INV); fml=r"g=0 \text{ jika } f\geq T,\; 255 \text{ sebaliknya}"
    result=cv2.cvtColor(thresh,cv2.COLOR_GRAY2BGR); p=int(gray[0,0])
    return {"result": result, "explanation": {
        "title": f"Thresholding ({mode})",
        "formula": fml, "description": f"Binarisasi dengan T={tv}.",
        "steps": [f"T={tv}, mode={mode}", f"gray[0,0]={p}", f"output={255 if p>=tv else 0}"],
        "pixel_before": get_pixel_matrix(gray), "pixel_after": get_pixel_matrix(thresh),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_mean_filter(img, params):
    ksize=int(params.get("ksize",3)); ksize=ksize+1 if ksize%2==0 else ksize
    result=cv2.blur(img,(ksize,ksize)); kv=round(1/(ksize*ksize),4)
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); patch=get_pixel_matrix(gray,n=ksize)
    flat=[gray[i,j] for i in range(ksize) for j in range(ksize)]
    return {"result": result, "explanation": {
        "title": f"Mean Filter ({ksize}×{ksize})",
        "formula": r"g(x,y) = \frac{1}{k^2}\sum_{m,n \in W} f(x+m, y+n)",
        "description": f"Rata-rata {ksize}×{ksize}={ksize*ksize} tetangga. Mengurangi noise acak.",
        "kernel": [[kv]*ksize for _ in range(ksize)],
        "steps": [f"Bobot=1/{ksize*ksize}={kv}", f"Rata-rata={round(sum(flat)/len(flat),2)}"],
        "pixel_before": patch, "pixel_after": get_pixel_matrix(result,n=ksize),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_median_filter(img, params):
    ksize=int(params.get("ksize",3)); ksize=ksize+1 if ksize%2==0 else ksize
    result=cv2.medianBlur(img,ksize); gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    flat=sorted([gray[i,j] for i in range(ksize) for j in range(ksize)])
    return {"result": result, "explanation": {
        "title": f"Median Filter ({ksize}×{ksize})",
        "formula": r"g(x,y) = \text{median}\{f(x+m, y+n) \;|\; m,n \in W\}",
        "description": f"Median dari {ksize}×{ksize} tetangga. Efektif untuk salt-and-pepper noise.",
        "steps": [f"Nilai terurut: {flat}", f"Median (ke-{len(flat)//2+1})={flat[len(flat)//2]}"],
        "pixel_before": get_pixel_matrix(gray,n=ksize), "pixel_after": get_pixel_matrix(result,n=ksize),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_sobel(img, params):
    direction=params.get("direction","both")
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); gb=cv2.GaussianBlur(gray,(3,3),0)
    sx=cv2.Sobel(gb,cv2.CV_64F,1,0,ksize=3); sy=cv2.Sobel(gb,cv2.CV_64F,0,1,ksize=3)
    if direction=="x": mag=cv2.convertScaleAbs(sx); fml=r"G_x=\begin{pmatrix}-1&0&1\\-2&0&2\\-1&0&1\end{pmatrix}*f"; kern=[[-1,0,1],[-2,0,2],[-1,0,1]]
    elif direction=="y": mag=cv2.convertScaleAbs(sy); fml=r"G_y=\begin{pmatrix}-1&-2&-1\\0&0&0\\1&2&1\end{pmatrix}*f"; kern=[[-1,-2,-1],[0,0,0],[1,2,1]]
    else: mag=np.clip(cv2.magnitude(sx,sy),0,255).astype(np.uint8); fml=r"G=\sqrt{G_x^2+G_y^2}"; kern=[[-1,0,1],[-2,0,2],[-1,0,1]]
    result=cv2.cvtColor(mag,cv2.COLOR_GRAY2BGR)
    return {"result": result, "explanation": {
        "title": f"Sobel Edge Detection ({direction})",
        "formula": fml, "description": "Deteksi tepi via gradien first-order.",
        "kernel": kern, "pixel_before": get_pixel_matrix(gray,n=3), "pixel_after": get_pixel_matrix(mag,n=3),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
        "steps": ["Kernel Sobel dikonvolusi dengan gambar grayscale", "Magnitude = √(Gx²+Gy²)"],
    }}

def op_enhance_pipeline(img, params):
    beta=int(params.get("beta",30)); alpha=float(params.get("alpha",1.3))
    s1=cv2.convertScaleAbs(img,alpha=1.0,beta=beta); s2=cv2.convertScaleAbs(s1,alpha=alpha,beta=0)
    blur=cv2.GaussianBlur(s2,(0,0),3); s3=cv2.addWeighted(s2,1.5,blur,-0.5,0)
    result=cv2.medianBlur(s3,3)
    return {"result": result, "explanation": {
        "title": "Enhancement Pipeline",
        "formula": r"g=\text{Median}(\text{Sharpen}(\alpha\cdot(f+\beta)))",
        "description": "Pipeline: Brightness→Contrast→Sharpening→Denoising.",
        "steps": [f"1. Brightness: g₁=f+{beta}", f"2. Contrast: g₂={alpha}×g₁", "3. Unsharp Mask: g₃=1.5×g₂−0.5×Blur", "4. Median: g₄=Median(g₃,3)"],
        "pipeline": [{"name":"Original","beta":0,"alpha":1.0},{"name":"+Brightness","beta":beta,"alpha":1.0},{"name":"+Contrast","beta":beta,"alpha":alpha},{"name":"+Sharpen+Denoise","beta":beta,"alpha":alpha}],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

# ══════════════════════════════════════════════════════
# NEW EDUCATIONAL OPERATIONS
# ══════════════════════════════════════════════════════

def op_saturation(img, params):
    """
    Saturasi: ubah kejenuhan warna via ruang HSV
    s > 0  → warna lebih jenuh/vivid
    s < 0  → warna memudar (menuju grayscale)
    """
    s_factor = float(params.get("saturation", 50))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    scale = 1.0 + s_factor / 100.0
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * scale, 0, 255)
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    p_h, p_s, p_v = [int(x) for x in cv2.cvtColor(img[0:1,0:1], cv2.COLOR_BGR2HSV)[0,0]]
    p_s_new = int(min(255, max(0, p_s * scale)))

    return {"result": result, "explanation": {
        "title": "Saturasi (Saturation)",
        "formula": r"S'(x,y) = \text{clip}(S(x,y) \times (1 + \frac{s}{100}),\;0,\;255)",
        "description": (
            f"Saturasi diubah sebesar s={s_factor}. "
            "Ruang warna dikonversi BGR→HSV, channel S (kejenuhan) dimodifikasi, lalu dikembalikan ke BGR. "
            "s=+100 menggandakan saturasi, s=-100 → gambar grayscale."
        ),
        "steps": [
            "1. BGR → HSV  (Hue: 0-180°, Saturation: 0-255, Value: 0-255)",
            f"   scale = 1 + {s_factor}/100 = {round(scale,2)}",
            f"2. Piksel [0,0] HSV asli: H={p_h}, S={p_s}, V={p_v}",
            f"3. S' = clip({p_s} × {round(scale,2)}, 0, 255) = {p_s_new}",
            "4. HSV → BGR  (konversi kembali ke format display)",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_hue_shift(img, params):
    """
    Hue Shift: putar roda warna sebesar N derajat via HSV
    """
    shift = int(params.get("hue", 30))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int32)
    hsv[:, :, 0] = (hsv[:, :, 0] + shift // 2) % 180
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    p_h = int(cv2.cvtColor(img[0:1,0:1], cv2.COLOR_BGR2HSV)[0,0,0])
    p_h_new = (p_h + shift // 2) % 180

    return {"result": result, "explanation": {
        "title": "Hue Shift (Pergeseran Warna)",
        "formula": r"H'(x,y) = (H(x,y) + \Delta h) \mod 180",
        "description": (
            f"Hue digeser {shift}°. Roda warna diputar: merah→kuning→hijau→biru→ungu→merah. "
            "OpenCV menggunakan rentang H: 0-180 (bukan 0-360)."
        ),
        "steps": [
            "1. BGR → HSV",
            f"   Δh = {shift}° → dalam OpenCV = {shift//2} (skala ½)",
            f"2. Piksel [0,0] Hue asli: {p_h} (={p_h*2}° aktual)",
            f"3. H' = ({p_h} + {shift//2}) mod 180 = {p_h_new}",
            "4. HSV → BGR",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_sharpness(img, params):
    """
    Sharpness via Unsharp Masking:
    g = clip(img + amount × (img - GaussianBlur(img)))
    """
    amount = float(params.get("amount", 1.0))

    blur = cv2.GaussianBlur(img, (0, 0), 2)
    result = cv2.convertScaleAbs(
        img.astype(np.float32) + amount * (img.astype(np.float32) - blur.astype(np.float32))
    )

    p_b = int(img[10, 10, 0])
    p_blur = int(blur[10, 10, 0])
    p_sharp = int(min(255, max(0, p_b + amount * (p_b - p_blur))))

    return {"result": result, "explanation": {
        "title": "Sharpness (Ketajaman) — Unsharp Masking",
        "formula": r"g(x,y) = \text{clip}(f(x,y) + a \cdot (f(x,y) - \text{Blur}(f(x,y))),\;0,\;255)",
        "description": (
            f"Unsharp Masking dengan amount={amount}. "
            "Blur dikurangi dari asli menghasilkan 'detail mask'. "
            "Detail mask ditambahkan kembali ke gambar asli."
        ),
        "steps": [
            "1. Buat blur: B = GaussianBlur(f, sigma=2)",
            f"   Amount a = {amount}",
            "2. Hitung detail mask: D = f − B",
            "3. Tambah ke asli: g = f + a × D",
            f"4. Piksel [10,10]: f={p_b}, B={p_blur}, D={p_b-p_blur}",
            f"   g = {p_b} + {amount}×{p_b-p_blur} = {p_sharp}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_gaussian_blur(img, params):
    """
    Gaussian Blur: kernel berbentuk Gaussian (pembobotan berbasis jarak)
    """
    sigma = float(params.get("sigma", 2.0))
    ksize = max(3, int(sigma * 3) | 1)

    result = cv2.GaussianBlur(img, (ksize, ksize), sigma)

    ax = np.arange(-(ksize//2), ksize//2 + 1)
    kernel_1d = np.exp(-ax**2 / (2 * sigma**2))
    kernel_1d /= kernel_1d.sum()
    kernel_2d = np.outer(kernel_1d, kernel_1d)
    kernel_2d_norm = kernel_2d / kernel_2d.sum()
    kernel_show = [[round(float(v), 4) for v in row] for row in kernel_2d_norm]

    return {"result": result, "explanation": {
        "title": f"Gaussian Blur (σ={sigma})",
        "formula": r"G(x,y) = \frac{1}{2\pi\sigma^2} e^{-\frac{x^2+y^2}{2\sigma^2}}",
        "description": (
            f"Gaussian Blur dengan σ={sigma}, kernel {ksize}×{ksize}. "
            "Piksel lebih dekat ke pusat mendapat bobot lebih besar (distribusi normal). "
            "Lebih halus dari Mean Filter karena tidak memotong frekuensi secara tiba-tiba."
        ),
        "kernel": kernel_show[:min(5, ksize)],
        "steps": [
            f"σ = {sigma}, ksize = {ksize}×{ksize}",
            f"G(0,0) = 1/(2π×{sigma}²) × e^0 → bobot terbesar di pusat",
            f"G(1,0) ≈ e^(-1/(2×{sigma}²)) × bobot pusat",
            "Total semua bobot = 1.0 (normalized)",
            "Setiap piksel = Σ(kernel × tetangga)",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_opacity(img, params):
    """
    Opacity: blend gambar dengan warna background (putih/hitam)
    """
    opacity_val = float(params.get("opacity", 50))  # 0-100
    bg_color = params.get("bg_color", "white")

    alpha = opacity_val / 100.0
    if bg_color == "black":
        bg = np.zeros_like(img)
    else:
        bg = np.full_like(img, 255)

    result = cv2.addWeighted(img, alpha, bg, 1.0 - alpha, 0)

    p = img[0, 0].tolist()
    bg_p = [255, 255, 255] if bg_color == "white" else [0, 0, 0]
    p_out = [round(alpha * a + (1 - alpha) * b) for a, b in zip(p, bg_p)]

    return {"result": result, "explanation": {
        "title": "Opacity (Transparansi)",
        "formula": r"g(x,y) = \alpha \cdot f(x,y) + (1-\alpha) \cdot B",
        "description": (
            f"Opacity {opacity_val}% dengan background {bg_color}. "
            "Semakin kecil opacity, gambar semakin transparan (bercampur dengan background). "
            "Di OpenCV: blending dengan warna solid karena tidak ada channel alpha di JPEG."
        ),
        "steps": [
            f"α = {opacity_val}/100 = {alpha}",
            f"Background B = {'putih (255,255,255)' if bg_color=='white' else 'hitam (0,0,0)'}",
            f"Piksel [0,0] asli: {p}",
            f"g = {alpha}×{p} + {1-alpha:.2f}×{bg_p}",
            f"g ≈ {p_out}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


# ══════════════════════════════════════════════════════
# OPERATIONS ROUTER
# ══════════════════════════════════════════════════════

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
    "saturation":       op_saturation,
    "hue_shift":        op_hue_shift,
    "sharpness":        op_sharpness,
    "gaussian_blur":    op_gaussian_blur,
    "opacity":          op_opacity,
    "mean_filter":      op_mean_filter,
    "median_filter":    op_median_filter,
    "sobel":            op_sobel,
    "enhance_pipeline": op_enhance_pipeline,
}

# ══════════════════════════════════════════════════════
# ADVANCED EDITOR API ROUTES
# ══════════════════════════════════════════════════════

@app.route("/api/editor/remove-bg", methods=["POST"])
def editor_remove_bg():
    """
    Background removal menggunakan GrabCut (OpenCV).
    Mengembalikan gambar PNG dengan alpha channel (transparansi).
    """
    try:
        data = request.get_json()
        img = decode_image(data.get("image"))
        h, w = img.shape[:2]

        mask     = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        margin = 0.10
        rect = (int(w*margin), int(h*margin), int(w*(1-2*margin)), int(h*(1-2*margin)))
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

        mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)

        b_ch, g_ch, r_ch = cv2.split(img)
        result_rgba = cv2.merge([b_ch, g_ch, r_ch, mask2])

        ok, buf = cv2.imencode(".png", result_rgba)
        b64 = "data:image/png;base64," + base64.b64encode(buf).decode()
        return jsonify({"result": b64, "method": "GrabCut"})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/editor/cutout", methods=["POST"])
def editor_cutout():
    """
    Object cutout via GrabCut dengan bounding box dari user.
    rect = {x, y, w, h} dalam koordinat piksel gambar.
    """
    try:
        data = request.get_json()
        img  = decode_image(data.get("image"))
        rect_data = data.get("rect", None)
        h, w = img.shape[:2]

        mask     = np.zeros((h, w), np.uint8)
        bgd      = np.zeros((1, 65), np.float64)
        fgd      = np.zeros((1, 65), np.float64)

        if rect_data:
            rx = max(0, int(rect_data["x"]))
            ry = max(0, int(rect_data["y"]))
            rw = max(10, min(int(rect_data["w"]), w - rx - 1))
            rh = max(10, min(int(rect_data["h"]), h - ry - 1))
            rect = (rx, ry, rw, rh)
        else:
            rect = (int(w*0.1), int(h*0.1), int(w*0.8), int(h*0.8))

        cv2.grabCut(img, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)

        b_ch, g_ch, r_ch = cv2.split(img)
        result_rgba = cv2.merge([b_ch, g_ch, r_ch, mask2])

        ok, buf = cv2.imencode(".png", result_rgba)
        b64 = "data:image/png;base64," + base64.b64encode(buf).decode()
        return jsonify({"result": b64})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/editor/apply", methods=["POST"])
def editor_apply():
    """
    Terapkan semua filter via OpenCV untuk export berkualitas tinggi.
    Lebih akurat dibanding CSS filter.
    """
    try:
        data   = request.get_json()
        img    = decode_image(data.get("image"))
        p      = data.get("params", {})

        # Brightness + Contrast
        alpha = 1.0 + float(p.get("contrast", 0)) / 100.0
        beta  = float(p.get("brightness", 0)) * 2.55
        img   = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

        # Saturation
        sat = float(p.get("saturation", 0))
        if sat != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:,:,1] = np.clip(hsv[:,:,1] * (1 + sat/100), 0, 255)
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Hue
        hue = int(p.get("hue", 0))
        if hue != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int32)
            hsv[:,:,0] = (hsv[:,:,0] + hue // 2) % 180
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Blur
        blur_v = float(p.get("blur", 0))
        if blur_v > 0:
            sigma = blur_v / 10.0
            ksize = max(3, int(sigma * 3) | 1)
            img = cv2.GaussianBlur(img, (ksize, ksize), sigma)

        # Sharpness (Unsharp Mask)
        sharp = float(p.get("sharpness", 0))
        if sharp > 0:
            blur_img = cv2.GaussianBlur(img, (0, 0), 2)
            img = cv2.convertScaleAbs(
                img.astype(np.float32) + (sharp/100*2) * (img.astype(np.float32) - blur_img.astype(np.float32))
            )

        # Opacity
        opacity_v = float(p.get("opacity", 100))
        if opacity_v < 100:
            a = opacity_v / 100.0
            white = np.full_like(img, 255)
            img = cv2.addWeighted(img, a, white, 1-a, 0)

        # Rotation
        angle = int(p.get("rotation", 0))
        if angle != 0:
            h, w = img.shape[:2]
            M = cv2.getRotationMatrix2D((w//2, h//2), -angle, 1)
            img = cv2.warpAffine(img, M, (w, h))

        # Flip
        if p.get("flipH"): img = cv2.flip(img, 1)
        if p.get("flipV"): img = cv2.flip(img, 0)

        return jsonify({"result": encode_image(img)})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ══════════════════════════════════════════════════════
# MAIN API ROUTE
# ══════════════════════════════════════════════════════

@app.route("/api/process", methods=["POST"])
def process_image():
    try:
        data      = request.get_json()
        operation = data.get("operation", "grayscale")
        params    = data.get("params", {})
        image_b64 = data.get("image")
        if not image_b64:
            return jsonify({"error": "Tidak ada gambar"}), 400
        if operation not in OPERATIONS:
            return jsonify({"error": f"Operasi '{operation}' tidak dikenal. Tersedia: {list(OPERATIONS.keys())}"}), 400
        img = decode_image(image_b64)
        out = OPERATIONS[operation](img, params)
        return jsonify({"before": image_b64, "after": encode_image(out["result"]), "explanation": out["explanation"]})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/operations", methods=["GET"])
def list_ops():
    return jsonify({"operations": list(OPERATIONS.keys())})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.0.0", "operations": len(OPERATIONS)})

# ── Serve React build ──────────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    file_path = os.path.join(FRONTEND_BUILD, path)
    if path and os.path.exists(file_path):
        return send_from_directory(FRONTEND_BUILD, path)
    return send_from_directory(FRONTEND_BUILD, "index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)