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

def encode_stage_preview(img: np.ndarray, max_dim: int = 380) -> str:
    """Encode an intermediate pipeline result as a small PNG (keeps API payload light)."""
    h, w = img.shape[:2]
    s = min(1.0, max_dim / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return encode_image(img)

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

def run_segmentation_pipeline(original: np.ndarray, rect: dict = None, work_max_dim: int = 640) -> dict:
    """
    Pipeline segmentasi citra klasik multi-tahap untuk background removal /
    object cutout berkualitas tinggi. Setiap tahap mengembalikan penjelasan
    edukasi (formula, tujuan, konsep matematis) + gambar pratinjau.

    original : citra BGR asli (resolusi penuh)
    rect     : {x,y,w,h} opsional dalam koordinat citra ASLI (untuk cutout terarah)
    """
    oh, ow = original.shape[:2]
    scale = min(1.0, work_max_dim / max(oh, ow))
    work = cv2.resize(original, (max(1,int(ow*scale)), max(1,int(oh*scale))), interpolation=cv2.INTER_AREA) \
           if scale < 1.0 else original.copy()
    wh, ww = work.shape[:2]

    stages = []

    # ── TAHAP 1: Bilateral Filtering ──────────────────────────────────
    denoised = cv2.bilateralFilter(work, d=9, sigmaColor=75, sigmaSpace=75)
    stages.append({
        "id": "bilateral", "order": 1,
        "title": "Bilateral Filtering",
        "objective": "Mengurangi noise sambil mempertahankan ketajaman tepi objek (edge-preserving smoothing).",
        "formula": r"BF[I]_p=\frac{1}{W_p}\sum_{q\in S} I_q\, f_r(\|I_p-I_q\|)\, g_s(\|p-q\|)",
        "math_concept": (
            "Menggabungkan dua kernel Gaussian: kernel spasial g_s (berdasarkan jarak piksel) dan kernel "
            "range f_r (berdasarkan perbedaan intensitas). Piksel tetangga yang nilainya jauh berbeda "
            "(kemungkinan besar tepi objek) diberi bobot kecil — sehingga noise berkurang tanpa mengaburkan tepi, "
            "berbeda dari Gaussian Blur biasa yang mengaburkan segalanya secara merata."
        ),
        "description": "Parameter: d=9 (diameter neighborhood), sigmaColor=75, sigmaSpace=75.",
        "image": encode_stage_preview(denoised),
    })

    # ── TAHAP 2: CLAHE pada channel L (Lab) ───────────────────────────
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch_lab = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l_ch)
    enhanced = cv2.cvtColor(cv2.merge([l_eq, a_ch, b_ch_lab]), cv2.COLOR_LAB2BGR)
    stages.append({
        "id": "clahe", "order": 2,
        "title": "CLAHE (Contrast Enhancement)",
        "objective": "Meningkatkan kontras lokal pada channel kecerahan agar batas objek-background lebih jelas.",
        "formula": r"L'(x,y) = \mathrm{clip}_{T}\big(H_{tile}(L(x,y))\big),\quad tile = 8\times 8",
        "math_concept": (
            "Citra dikonversi ke ruang warna Lab agar kecerahan (L) terpisah dari informasi warna (a,b). "
            "CLAHE membagi channel L menjadi blok 8×8, melakukan ekualisasi histogram per-blok dengan batas "
            "klip (clipLimit=3.0) untuk mencegah over-amplifikasi noise, lalu interpolasi bilinear antar blok "
            "agar transisi mulus. Channel warna (a,b) tidak disentuh sehingga warna asli tetap akurat."
        ),
        "description": "Diterapkan hanya pada channel L (Lightness), bukan ke seluruh citra BGR.",
        "image": encode_stage_preview(enhanced),
    })

    # ── TAHAP 3: GrabCut (segmentasi awal) ────────────────────────────
    mask = np.zeros((wh, ww), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    if rect:
        rx = max(0, int(rect.get("x", 0) * scale))
        ry = max(0, int(rect.get("y", 0) * scale))
        rw = max(10, min(int(rect.get("w", ww) * scale), ww - rx - 1))
        rh = max(10, min(int(rect.get("h", wh) * scale), wh - ry - 1))
        gc_rect = (rx, ry, rw, rh)
    else:
        m = 0.08
        gc_rect = (int(ww * m), int(wh * m), int(ww * (1 - 2*m)), int(wh * (1 - 2*m)))
    cv2.grabCut(enhanced, mask, gc_rect, bgd_model, fgd_model, 6, cv2.GC_INIT_WITH_RECT)
    grabcut_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)
    stages.append({
        "id": "grabcut", "order": 3,
        "title": "GrabCut Segmentation",
        "objective": "Segmentasi awal foreground vs background menggunakan Gaussian Mixture Model + Graph Cut.",
        "formula": r"E(\alpha)=\sum_{p} U(\alpha_p) + \sum_{p,q \in N} V(\alpha_p,\alpha_q)",
        "math_concept": (
            "Foreground & background masing-masing dimodelkan dengan GMM 5-komponen warna. Algoritma mencari "
            "pemisahan optimal via Min-Cut/Max-Flow pada graph piksel: meminimalkan energi U (kecocokan piksel "
            "terhadap model warna GMM) ditambah V (penalti diskontinuitas antar piksel bertetangga)."
        ),
        "description": f"Rectangle inisialisasi: {gc_rect}, 6 iterasi optimisasi GMM.",
        "image": encode_stage_preview(grabcut_mask),
    })

    # ── TAHAP 4: Morphological Opening ─────────────────────────────────
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(grabcut_mask, cv2.MORPH_OPEN, k_open, iterations=2)
    stages.append({
        "id": "opening", "order": 4,
        "title": "Morphological Opening",
        "objective": "Menghapus bintik/noise kecil yang salah terdeteksi sebagai bagian foreground.",
        "formula": r"A \circ B = (A \ominus B) \oplus B",
        "math_concept": (
            "Operasi Erosi (mengikis tepi region) diikuti Dilasi (melebarkan kembali), menggunakan elemen "
            "struktur elips 5×5. Objek yang lebih sempit dari elemen struktur akan hilang total, sedangkan "
            "objek utama yang cukup besar bentuknya tetap dipertahankan."
        ),
        "description": "Structuring element: ellipse 5×5, 2 iterasi.",
        "image": encode_stage_preview(opened),
    })

    # ── TAHAP 5: Morphological Closing ─────────────────────────────────
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, k_close, iterations=2)
    stages.append({
        "id": "closing", "order": 5,
        "title": "Morphological Closing",
        "objective": "Menutup lubang-lubang kecil di dalam area objek agar mask menjadi solid/utuh.",
        "formula": r"A \bullet B = (A \oplus B) \ominus B",
        "math_concept": (
            "Kebalikan dari Opening: Dilasi diikuti Erosi, menggunakan elemen struktur elips 9×9 (lebih besar "
            "agar mampu menutup celah yang lebih lebar). Lubang atau celah yang lebih kecil dari elemen "
            "struktur akan tertutup tanpa mengubah ukuran objek secara keseluruhan."
        ),
        "description": "Structuring element: ellipse 9×9, 2 iterasi.",
        "image": encode_stage_preview(closed),
    })

    # ── TAHAP 6: Distance Transform + Watershed ───────────────────────
    dist = cv2.distanceTransform(closed, cv2.DIST_L2, 5)
    dist_norm = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    try:
        _, sure_fg = cv2.threshold(dist, 0.45 * dist.max(), 255, 0)
        sure_fg = np.uint8(sure_fg)
        sure_bg = cv2.dilate(closed, k_open, iterations=3)
        unknown = cv2.subtract(sure_bg, sure_fg)
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        markers_ws = cv2.watershed(enhanced, markers.astype(np.int32))
        watershed_mask = np.zeros((wh, ww), np.uint8)
        watershed_mask[markers_ws > 1] = 255
    except Exception:
        watershed_mask = closed.copy()
    stages.append({
        "id": "watershed", "order": 6,
        "title": "Distance Transform + Watershed",
        "objective": "Memperhalus batas objek dan memisahkan bagian yang saling menempel.",
        "formula": r"D(p)=\min_{q \in \partial F}\|p-q\|_2 \;\Rightarrow\; \text{relief topografi untuk Watershed}",
        "math_concept": (
            "Distance Transform menghitung jarak Euclidean tiap piksel foreground ke tepi terdekat, "
            "menghasilkan 'peta ketinggian' (puncak = pusat objek). Watershed memperlakukan peta ini seperti "
            "relief topografi: air 'dialirkan' dari titik tertinggi hingga bertemu di garis pemisah (watershed line), "
            "menghasilkan batas objek yang presisi."
        ),
        "description": "sure_fg dari 45% jarak maksimum, sure_bg dari dilasi 3 iterasi.",
        "image": encode_stage_preview(dist_norm),
        "secondary_image": encode_stage_preview(watershed_mask),
    })

    # ── TAHAP 7: Sobel + Laplacian Edge Fusion ────────────────────────
    gray_e = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    sx = cv2.Sobel(gray_e, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray_e, cv2.CV_64F, 0, 1, ksize=3)
    sobel_mag = cv2.normalize(np.sqrt(sx**2 + sy**2), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    lap = cv2.Laplacian(gray_e, cv2.CV_64F, ksize=3)
    lap_norm = cv2.normalize(np.abs(lap), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    edge_fused = cv2.addWeighted(sobel_mag, 0.6, lap_norm, 0.4, 0)
    band = cv2.subtract(cv2.dilate(watershed_mask, k_open, iterations=2),
                         cv2.erode(watershed_mask, k_open, iterations=2))
    edge_in_band = cv2.bitwise_and(edge_fused, edge_fused, mask=band)
    _, strong_edges = cv2.threshold(edge_in_band, 60, 255, cv2.THRESH_BINARY)
    refined_mask = cv2.bitwise_or(watershed_mask, strong_edges)
    stages.append({
        "id": "edges", "order": 7,
        "title": "Sobel + Laplacian Edge Fusion",
        "objective": "Menjaga detail kontur tipis (rambut, bulu, tepi tajam) yang berisiko hilang saat morphology.",
        "formula": r"G=\sqrt{G_x^2+G_y^2} \quad\quad \nabla^2 f = \frac{\partial^2 f}{\partial x^2}+\frac{\partial^2 f}{\partial y^2}",
        "math_concept": (
            "Sobel (turunan orde-1) mendeteksi tepi terarah dan relatif tahan noise. Laplacian (turunan orde-2) "
            "sangat sensitif terhadap detail halus/tipis namun rentan noise. Kombinasi 60% Sobel + 40% Laplacian "
            "dihitung hanya pada pita tipis di sekitar batas mask (boundary band) untuk mempertegas kontur halus."
        ),
        "description": "Edge map difusikan hanya pada boundary band, bukan ke seluruh citra.",
        "image": encode_stage_preview(edge_fused),
    })

    # ── TAHAP 8: Contour Optimization + Connected Component Analysis ──
    contours, _ = cv2.findContours(refined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_mask = np.zeros((wh, ww), np.uint8)
    if contours:
        main_c = max(contours, key=cv2.contourArea)
        epsilon = 0.0015 * cv2.arcLength(main_c, True)
        smooth_c = cv2.approxPolyDP(main_c, epsilon, True)
        cv2.drawContours(contour_mask, [smooth_c], -1, 255, thickness=cv2.FILLED)
    else:
        contour_mask = refined_mask.copy()

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(contour_mask, connectivity=8)
    min_area = 0.005 * wh * ww
    cca_mask = np.zeros((wh, ww), np.uint8)
    kept = 0
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            cca_mask[labels == i] = 255
            kept += 1
    if kept == 0:
        cca_mask = contour_mask.copy()
    stages.append({
        "id": "contour_cca", "order": 8,
        "title": "Contour Optimization + Connected Components",
        "objective": "Menghaluskan garis kontur dan membuang fragmen kecil yang bukan bagian objek utama.",
        "formula": r"\epsilon = 0.0015 \times \text{Perimeter}, \quad \text{Area}(C_i) \geq 0.5\% \times (W \times H)",
        "math_concept": (
            "approxPolyDP menyederhanakan kontur menggunakan algoritma Douglas-Peucker untuk menghilangkan "
            "jitter piksel pada garis tepi. Connected Component Analysis melabeli setiap region terpisah "
            "(8-connectivity) dan membuang region yang luasnya di bawah ambang batas (dianggap noise/fragmen)."
        ),
        "description": f"{max(0,num_labels-1)} komponen ditemukan, {kept} dipertahankan (area ≥ 0.5% dari citra).",
        "image": encode_stage_preview(cca_mask),
    })

    # ── TAHAP 9: Alpha Matting + Gaussian Feathering ──────────────────
    sure_fg2 = cv2.erode(cca_mask, k_open, iterations=2)
    sure_bg2 = cv2.bitwise_not(cv2.dilate(cca_mask, k_open, iterations=3))
    dist_in  = cv2.distanceTransform(cca_mask, cv2.DIST_L2, 5)
    dist_out = cv2.distanceTransform(cv2.bitwise_not(cca_mask), cv2.DIST_L2, 5)
    band_width = 8.0
    alpha_f = np.where(
        cca_mask > 0,
        np.clip(dist_in / band_width, 0, 1),
        np.clip(1 - dist_out / band_width, 0, 1),
    ).astype(np.float32)
    alpha_feathered = cv2.GaussianBlur(alpha_f, (9, 9), 2.0)
    alpha_final = np.clip(alpha_feathered * 255, 0, 255).astype(np.uint8)
    stages.append({
        "id": "matting", "order": 9,
        "title": "Alpha Matting + Gaussian Feathering",
        "objective": "Menghasilkan transisi tepi yang halus & anti-alias, bukan tepi keras berpiksel (jaggies).",
        "formula": r"I = \alpha F + (1-\alpha) B, \quad \alpha(x,y) = \mathrm{blur}\Big(\min\big(\tfrac{D_{in}}{d},1\big)\Big)",
        "math_concept": (
            "Model compositing alpha matting klasik: tiap piksel adalah campuran Foreground (F) dan Background "
            "(B) sesuai nilai alpha ∈ [0,1]. Alpha dibangun dari Distance Transform (jarak ke tepi mask, "
            "dinormalisasi dalam band 8px) lalu dihaluskan dengan Gaussian Blur agar transisi lembut."
        ),
        "description": "Band transisi 8px, Gaussian kernel 9×9 σ=2.0.",
        "image": encode_stage_preview(alpha_final),
    })

    # ── Upscale alpha ke resolusi asli & komposit hasil akhir ─────────
    alpha_full = cv2.resize(alpha_final, (ow, oh), interpolation=cv2.INTER_LINEAR)
    b_ch, g_ch, r_ch = cv2.split(original)
    result_rgba = cv2.merge([b_ch, g_ch, r_ch, alpha_full])

    hist_before = get_histogram(original)
    gray_full = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    fg_pixels = gray_full[alpha_full > 127]
    if fg_pixels.size == 0:
        hist_after = hist_before
    else:
        h_counts, _ = np.histogram(fg_pixels, bins=256, range=(0, 256))
        h_counts = h_counts.astype(np.float32)
        hist_after = (h_counts / h_counts.max()).tolist() if h_counts.max() > 0 else h_counts.tolist()

    coverage_pct = round(float(np.sum(alpha_full > 127)) / (ow * oh) * 100, 1)

    return {
        "result_rgba": result_rgba,
        "stages": stages,
        "histogram_before": hist_before,
        "histogram_after": hist_after,
        "coverage_pct": coverage_pct,
        "work_resolution": f"{ww}×{wh}",
        "original_resolution": f"{ow}×{oh}",
    }



def order_points(pts: np.ndarray) -> np.ndarray:
    """Urutkan 4 titik sudut menjadi [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]          # top-left  → jumlah x+y terkecil
    rect[2] = pts[np.argmax(s)]          # bottom-right → jumlah x+y terbesar
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]       # top-right → selisih x-y terkecil
    rect[3] = pts[np.argmax(diff)]       # bottom-left → selisih x-y terbesar
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray):
    """Warp region 4-titik menjadi tampilan top-down rectangular (deskew + crop)."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a  = np.linalg.norm(br - bl)
    width_b  = np.linalg.norm(tr - tl)
    max_w    = max(int(width_a), int(width_b), 10)

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h    = max(int(height_a), int(height_b), 10)

    dst = np.array([[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_w, max_h))
    return warped, M, max_w, max_h


def find_document_quad(work: np.ndarray):
    """
    Deteksi 4 sudut dokumen pada citra kerja (work resolution).
    Mengembalikan (quad_4pts atau None, visualisasi_kontur, edge_map, blur_map).
    """
    wh, ww = work.shape[:2]
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    edges_dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)

    contours, _ = cv2.findContours(edges_dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:6]

    quad = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.15 * wh * ww:
            quad = approx.reshape(4, 2).astype(np.float32)
            break

    # Fallback tier 2: pakai minAreaRect dari kontur terbesar jika tidak ada quad sempurna
    if quad is None and contours and cv2.contourArea(contours[0]) > 0.12 * wh * ww:
        rect = cv2.minAreaRect(contours[0])
        quad = cv2.boxPoints(rect).astype(np.float32)

    contour_vis = work.copy()
    if quad is not None:
        cv2.drawContours(contour_vis, [quad.astype(int)], -1, (80, 220, 120), 3)
        for (x, y) in quad:
            cv2.circle(contour_vis, (int(x), int(y)), 6, (80, 220, 120), -1)
    else:
        cv2.putText(contour_vis, "Tepi dokumen tidak terdeteksi - pakai frame penuh",
                    (10, wh - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 220, 120), 1, cv2.LINE_AA)

    return quad, contour_vis, edges_dilated, blur


def run_document_scan_pipeline(original: np.ndarray, work_max_dim: int = 900) -> dict:
    """
    Pipeline restorasi dokumen/foto bergaya CamScanner. Mendeteksi tepi dokumen,
    meluruskan perspektif, menghapus bayangan, mengurangi noise, mempertajam detail,
    lalu menghasilkan 3 mode output: grayscale, hitam-putih (binerisasi), dan color enhanced.
    """
    oh, ow = original.shape[:2]
    scale = min(1.0, work_max_dim / max(oh, ow))
    work = cv2.resize(original, (max(1, int(ow * scale)), max(1, int(oh * scale))),
                       interpolation=cv2.INTER_AREA) if scale < 1.0 else original.copy()

    stages = []

    # ── TAHAP 1: Grayscale + Gaussian Blur ────────────────────────────
    quad, contour_vis, edges_dilated, blur = find_document_quad(work)
    stages.append({
        "id": "preprocess", "order": 1,
        "title": "Grayscale + Gaussian Blur",
        "objective": "Menyederhanakan citra ke satu channel dan meredam noise sebelum deteksi tepi.",
        "formula": r"L=0.299R+0.587G+0.114B,\quad B(x,y)=G_{\sigma}(x,y)*L(x,y)",
        "math_concept": (
            "Citra dikonversi ke grayscale agar deteksi tepi tidak terganggu variasi warna, "
            "lalu di-blur dengan Gaussian 5×5 agar tekstur kertas/noise sensor tidak terdeteksi "
            "sebagai tepi palsu pada tahap Canny berikutnya."
        ),
        "description": "Kernel Gaussian 5×5, σ otomatis dari OpenCV.",
        "image": encode_stage_preview(blur),
    })

    # ── TAHAP 2: Canny Edge Detection + Dilasi ────────────────────────
    stages.append({
        "id": "edges", "order": 2,
        "title": "Canny Edge Detection",
        "objective": "Menemukan garis tepi tajam (batas kertas vs latar belakang/meja).",
        "formula": r"G=\sqrt{G_x^2+G_y^2},\quad \text{Hysteresis}(G\,|\,T_{low}=50,\,T_{high}=150)",
        "math_concept": (
            "Canny menghitung gradien (mirip Sobel), melakukan Non-Maximum Suppression untuk "
            "menipiskan tepi menjadi 1 piksel, lalu hysteresis thresholding (dua ambang batas) untuk "
            "menyambung tepi yang kuat dan membuang tepi lemah yang terisolasi. Dilasi 2 iterasi "
            "menutup celah kecil pada garis tepi yang terputus."
        ),
        "description": "Threshold Canny: low=50, high=150. Dilasi kernel 5×5, 2 iterasi.",
        "image": encode_stage_preview(edges_dilated),
    })

    # ── TAHAP 3: Contour Detection + Deteksi Quad Dokumen ─────────────
    stages.append({
        "id": "contour", "order": 3,
        "title": "Contour Detection + Localisasi 4 Sudut",
        "objective": "Menemukan kontur terbesar berbentuk segiempat yang mewakili batas dokumen.",
        "formula": r"\epsilon=0.02\times\text{Perimeter}(C),\quad |\text{approxPolyDP}(C,\epsilon)|=4",
        "math_concept": (
            "Semua kontur diurutkan berdasarkan luas (terbesar dahulu). approxPolyDP (algoritma "
            "Douglas-Peucker) menyederhanakan tiap kontur; jika hasilnya tepat 4 titik dengan luas "
            "signifikan (>15% area citra), itu dianggap sudut dokumen. Jika tidak ditemukan, sistem "
            "fallback ke minAreaRect (rotated bounding box) dari kontur terbesar."
        ),
        "description": f"Dokumen {'terdeteksi' if quad is not None else 'TIDAK terdeteksi — memakai frame penuh'}.",
        "image": encode_stage_preview(contour_vis),
    })

    # ── TAHAP 4: Perspective Transform (Deskew + Auto-Crop) ───────────
    if quad is not None:
        pts_full = quad / scale  # map titik dari resolusi kerja → resolusi asli
        warped_color, M, mw, mh = four_point_transform(original, pts_full)
        doc_detected = True
    else:
        warped_color, mw, mh = original.copy(), ow, oh
        doc_detected = False

    # Batasi resolusi proses lanjutan agar tetap responsif
    proc_max = 1600
    pscale = min(1.0, proc_max / max(mw, mh))
    if pscale < 1.0:
        warped_color = cv2.resize(warped_color, (int(mw * pscale), int(mh * pscale)), interpolation=cv2.INTER_AREA)

    stages.append({
        "id": "perspective", "order": 4,
        "title": "Perspective Transform (Deskew + Auto-Crop)",
        "objective": "Meluruskan kemiringan & sudut pandang dokumen menjadi tampilan tegak lurus dari atas, sekaligus memotong latar belakang.",
        "formula": r"\begin{pmatrix}x'\\y'\\w'\end{pmatrix}=H\begin{pmatrix}x\\y\\1\end{pmatrix},\quad H=\text{getPerspectiveTransform}(src_4,dst_4)",
        "math_concept": (
            "Homography H (matriks 3×3) dihitung dari 4 titik sudut dokumen menuju 4 titik persegi "
            "panjang tujuan. Transformasi ini memetakan ulang setiap piksel sehingga dokumen yang "
            "difoto miring/dari sudut tertentu menjadi tampak seperti hasil pindai datar (flatbed scan)."
        ),
        "description": f"Output: {mw}×{mh}px (sebelum cap resolusi proses).",
        "image": encode_stage_preview(warped_color),
    })

    warped_gray = cv2.cvtColor(warped_color, cv2.COLOR_BGR2GRAY)

    # ── TAHAP 5: Shadow Removal / Koreksi Iluminasi ───────────────────
    bg_estimate = cv2.medianBlur(cv2.dilate(warped_gray, np.ones((7, 7), np.uint8)), 21)
    diff = 255 - cv2.absdiff(warped_gray, bg_estimate)
    shadow_removed = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    lab = cv2.cvtColor(warped_color, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch_lab = cv2.split(lab)
    l_corrected = cv2.normalize(
        cv2.addWeighted(l_ch, 1.0, cv2.medianBlur(cv2.dilate(l_ch, np.ones((7, 7), np.uint8)), 21), -1.0, 255),
        None, 0, 255, cv2.NORM_MINMAX,
    ).astype(np.uint8)
    color_shadow_fixed = cv2.cvtColor(cv2.merge([l_corrected, a_ch, b_ch_lab]), cv2.COLOR_LAB2BGR)

    stages.append({
        "id": "shadow", "order": 5,
        "title": "Shadow Removal (Koreksi Iluminasi)",
        "objective": "Menghilangkan bayangan tangan/lipatan dan pencahayaan tidak merata pada permukaan dokumen.",
        "formula": r"B_{est}=\text{median}_{21}\big(\text{dilate}_{7\times7}(I)\big),\quad I'=255-|I-B_{est}|",
        "math_concept": (
            "Dilasi dengan kernel besar menghilangkan detail teks/garis, menyisakan estimasi pola "
            "pencahayaan latar (background illumination map). Piksel asli dibandingkan terhadap peta "
            "ini — area yang lebih gelap dari sekitarnya secara lokal (bayangan) dinaikkan kembali "
            "mendekati putih, sementara teks/garis gelap tetap kontras."
        ),
        "description": "Dilasi 7×7, Median Blur kernel 21 untuk estimasi background.",
        "image": encode_stage_preview(shadow_removed),
    })

    # ── TAHAP 6: Noise Reduction ───────────────────────────────────────
    denoised_gray = cv2.fastNlMeansDenoising(shadow_removed, h=10, templateWindowSize=7, searchWindowSize=21)
    denoised_color = cv2.bilateralFilter(color_shadow_fixed, d=7, sigmaColor=50, sigmaSpace=50)
    stages.append({
        "id": "denoise", "order": 6,
        "title": "Noise Reduction",
        "objective": "Membersihkan bintik noise sensor kamera tanpa mengaburkan tepi teks.",
        "formula": r"NL[I]_p=\frac{1}{Z_p}\sum_{q\in S}w(p,q)\,I_q,\quad w(p,q)=e^{-\|N(p)-N(q)\|^2/h^2}",
        "math_concept": (
            "Non-Local Means Denoising (untuk jalur grayscale/B&W) membandingkan patch piksel di "
            "seluruh citra, bukan hanya tetangga lokal — patch yang mirip diberi bobot tinggi meski "
            "berjauhan, menghasilkan reduksi noise yang sangat bersih untuk teks. Jalur warna memakai "
            "Bilateral Filter (lebih cepat) agar gradasi warna tetap natural."
        ),
        "description": "Grayscale: fastNlMeansDenoising h=10. Warna: Bilateral d=7.",
        "image": encode_stage_preview(denoised_gray),
    })

    # ── TAHAP 7: Sharpening (Unsharp Masking) ─────────────────────────
    blur_g = cv2.GaussianBlur(denoised_gray, (0, 0), 2)
    sharpened_gray = cv2.convertScaleAbs(cv2.addWeighted(denoised_gray, 1.5, blur_g, -0.5, 0))
    blur_c = cv2.GaussianBlur(denoised_color, (0, 0), 2)
    sharpened_color = cv2.convertScaleAbs(cv2.addWeighted(denoised_color, 1.3, blur_c, -0.3, 0))
    stages.append({
        "id": "sharpen", "order": 7,
        "title": "Sharpening (Unsharp Masking)",
        "objective": "Mempertegas tepi huruf & garis agar teks terbaca jelas seperti hasil pindai asli.",
        "formula": r"g=f+a\cdot(f-\text{Blur}(f)),\quad a_{gray}=1.5,\;a_{color}=1.3",
        "math_concept": (
            "Versi blur dari citra dikurangkan dari aslinya untuk mendapatkan 'lapisan detail', lalu "
            "detail ini ditambahkan kembali dengan bobot lebih — menonjolkan tepi tajam tanpa mengubah "
            "area datar/seragam."
        ),
        "description": "Gaussian σ=2 untuk basis blur, amount 1.5 (gray) / 1.3 (warna).",
        "image": encode_stage_preview(sharpened_gray),
    })

    # ── TAHAP 8: Adaptive Thresholding + Output Modes ─────────────────
    bw = cv2.adaptiveThreshold(
        sharpened_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10
    )
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    grayscale_mode = clahe.apply(sharpened_gray)

    lab2 = cv2.cvtColor(sharpened_color, cv2.COLOR_BGR2LAB)
    l2, a2, b2 = cv2.split(lab2)
    l2_eq = clahe.apply(l2)
    color_mode = cv2.cvtColor(cv2.merge([l2_eq, a2, b2]), cv2.COLOR_LAB2BGR)

    stages.append({
        "id": "threshold", "order": 8,
        "title": "Adaptive Thresholding + Output Modes",
        "objective": "Membuat versi biner hitam-putih kontras tinggi khas dokumen scan, plus 2 mode output lain.",
        "formula": r"g(x,y)=\begin{cases}255 & f(x,y) > \mu_{block}(x,y) - C\\0 & \text{sebaliknya}\end{cases}",
        "math_concept": (
            "Berbeda dari thresholding global (satu nilai T untuk seluruh citra), adaptive threshold "
            "menghitung ambang batas lokal μ (rata-rata Gaussian tetangga blockSize=25) per-piksel "
            "dikurangi konstanta C=10 — sehingga tetap akurat meski pencahayaan sedikit tidak merata "
            "antar area kertas. Mode Grayscale & Warna memakai CLAHE untuk kontras tanpa binerisasi."
        ),
        "description": "Adaptive Gaussian, blockSize=25, C=10. CLAHE clipLimit=2.0, tile 8×8.",
        "image": encode_stage_preview(bw),
    })

    hist_before = get_histogram(original)
    hist_after = get_histogram(cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR))

    return {
        "grayscale": encode_image(cv2.cvtColor(grayscale_mode, cv2.COLOR_GRAY2BGR)),
        "bw": encode_image(cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)),
        "color": encode_image(color_mode),
        "stages": stages,
        "doc_detected": doc_detected,
        "output_resolution": f"{sharpened_gray.shape[1]}×{sharpened_gray.shape[0]}",
        "histogram_before": hist_before,
        "histogram_after": hist_after,
    }


# ══════════════════════════════════════════════════════
# ADVANCED EDITOR API ROUTES
# ══════════════════════════════════════════════════════

@app.route("/api/editor/scan-document", methods=["POST"])
def editor_scan_document():
    """
    Restorasi & pemindaian dokumen bergaya CamScanner — pipeline CV klasik 8-tahap
    (Grayscale+Blur → Canny → Contour+Quad → Perspective Transform → Shadow Removal
     → Noise Reduction → Sharpening → Adaptive Threshold).
    Mengembalikan 3 varian output (grayscale, hitam-putih, color enhanced) sekaligus
    breakdown edukasi tiap tahap, agar pengguna bisa beralih mode tanpa request ulang.
    """
    try:
        data = request.get_json()
        img = decode_image(data.get("image"))
        out = run_document_scan_pipeline(img)
        return jsonify({
            "grayscale": out["grayscale"],
            "bw": out["bw"],
            "color": out["color"],
            "method": "Document Scanner Pipeline (8 tahap)",
            "stages": out["stages"],
            "doc_detected": out["doc_detected"],
            "output_resolution": out["output_resolution"],
            "histogram_before": out["histogram_before"],
            "histogram_after": out["histogram_after"],
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/editor/cutout", methods=["POST"])
def editor_cutout():
    """
    Object cutout terarah (bounding box dari user) menggunakan pipeline
    CV klasik 9-tahap yang sama dengan remove-bg, di-seed oleh rect user.
    rect = {x, y, w, h} dalam koordinat piksel gambar ASLI.
    """
    try:
        data = request.get_json()
        img = decode_image(data.get("image"))
        rect_data = data.get("rect", None)
        out = run_segmentation_pipeline(img, rect=rect_data)
        return jsonify({
            "result": encode_rgba(out["result_rgba"]),
            "method": "Classical CV Pipeline (9 tahap)",
            "stages": out["stages"],
            "histogram_before": out["histogram_before"],
            "histogram_after": out["histogram_after"],
            "coverage_pct": out["coverage_pct"],
        })
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