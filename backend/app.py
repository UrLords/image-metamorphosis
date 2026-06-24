import os, base64, math, json, time, binascii
from functools import wraps
import numpy as np
import cv2
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from dotenv import load_dotenv

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials
except Exception:
    firebase_admin = None
    firebase_auth = None
    credentials = None

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024)))

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", f"{FRONTEND_URL},http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "12000000"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "40"))

CORS(
    app,
    resources={r"/api/*": {"origins": CORS_ORIGINS}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
)

FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
_RATE_BUCKETS = {}


def init_firebase():
    if not firebase_admin or firebase_admin._apps:
        return
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_base64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    try:
        if service_account_base64:
            decoded = base64.b64decode(service_account_base64).decode("utf-8")
            cred = credentials.Certificate(json.loads(decoded))
            firebase_admin.initialize_app(cred)
        elif service_account_json:
            if os.path.exists(service_account_json):
                cred = credentials.Certificate(service_account_json)
            else:
                cred = credentials.Certificate(json.loads(service_account_json))
            firebase_admin.initialize_app(cred)
        elif project_id:
            firebase_admin.initialize_app(options={"projectId": project_id})
    except Exception as exc:
        print(f"[security] Firebase init failed: {exc}")


init_firebase()


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.headers.get("X-Forwarded-Proto") == "https" or request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def get_client_key():
    auth_header = request.headers.get("Authorization", "")
    token_hint = auth_header[-24:] if auth_header.startswith("Bearer ") else ""
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.remote_addr or "unknown"
    return f"{ip}:{token_hint}"


def rate_limited():
    now = time.time()
    key = get_client_key()
    bucket = [ts for ts in _RATE_BUCKETS.get(key, []) if now - ts < RATE_LIMIT_WINDOW]
    if len(bucket) >= RATE_LIMIT_MAX:
        _RATE_BUCKETS[key] = bucket
        return True
    bucket.append(now)
    _RATE_BUCKETS[key] = bucket
    return False


def require_firebase_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if rate_limited():
            return jsonify({"error": "Terlalu banyak request. Coba lagi sebentar."}), 429

        if not REQUIRE_AUTH:
            g.user = None
            return fn(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Login diperlukan untuk memakai fitur ini."}), 401

        if not firebase_admin or not firebase_admin._apps or firebase_auth is None:
            return jsonify({"error": "Firebase auth belum dikonfigurasi di backend."}), 503

        token = auth_header.split(" ", 1)[1].strip()
        try:
            g.user = firebase_auth.verify_id_token(token, check_revoked=True)
        except Exception:
            return jsonify({"error": "Token login tidak valid atau sudah kedaluwarsa."}), 401

        return fn(*args, **kwargs)

    return wrapper
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# HELPERS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def decode_image(b64: str) -> np.ndarray:
    if not isinstance(b64, str) or "," not in b64:
        raise ValueError("Format gambar tidak valid")
    header, data = b64.split(",", 1)
    if not header.startswith("data:image/"):
        raise ValueError("File harus berupa gambar")
    if len(data) > app.config["MAX_CONTENT_LENGTH"] * 2:
        raise ValueError("Ukuran gambar terlalu besar")
    try:
        arr = np.frombuffer(base64.b64decode(data, validate=True), dtype=np.uint8)
    except (binascii.Error, ValueError):
        raise ValueError("Base64 gambar tidak valid")
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Gambar tidak valid")
    h, w = img.shape[:2]
    if h * w > MAX_IMAGE_PIXELS:
        raise ValueError(f"Resolusi gambar terlalu besar. Maksimum {MAX_IMAGE_PIXELS} piksel.")
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

def _hist_counts(channel: np.ndarray) -> np.ndarray:
    return cv2.calcHist([channel], [0], None, [256], [0, 256]).reshape(-1)


def _scale_hist(hist: np.ndarray, max_value: float) -> list:
    if max_value <= 0:
        return [0.0] * 256
    scaled = hist.astype(np.float32) / max_value
    return [float(v) if math.isfinite(float(v)) else 0.0 for v in scaled]


def get_histogram(img: np.ndarray) -> dict:
    try:
        img = img.astype(np.uint8) if img.dtype != np.uint8 else img
        if len(img.shape) == 2:
            hist = _hist_counts(img)
            lum = _scale_hist(hist, float(hist.max()))
            return {"red": [], "green": [], "blue": [], "luminance": lum}

        b, g, r = cv2.split(img[:, :, :3])
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        red_hist = _hist_counts(r)
        green_hist = _hist_counts(g)
        blue_hist = _hist_counts(b)
        lum_hist = _hist_counts(gray)
        max_value = float(max(red_hist.max(), green_hist.max(), blue_hist.max(), lum_hist.max()))
        return {
            "red": _scale_hist(red_hist, max_value),
            "green": _scale_hist(green_hist, max_value),
            "blue": _scale_hist(blue_hist, max_value),
            "luminance": _scale_hist(lum_hist, max_value),
        }
    except Exception:
        empty = [0.0] * 256
        return {"red": empty, "green": empty, "blue": empty, "luminance": empty}

def op_grayscale(img, params):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    b, g, r_ = int(img[0,0,0]), int(img[0,0,1]), int(img[0,0,2])
    lum = round(0.299*r_ + 0.587*g + 0.114*b, 2)
    return {"result": result, "explanation": {
        "title": "Konversi Grayscale",
        "formula": r"L = 0.299R + 0.587G + 0.114B",
        "description": "Setiap piksel RGB â†’ satu nilai luminance. Bobot berbeda karena mata manusia lebih sensitif terhadap hijau.",
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "steps": [f"R={r_}, G={g}, B={b}", f"L = 0.299Ã—{r_} + 0.587Ã—{g} + 0.114Ã—{b} = {lum} â‰ˆ {int(lum)}"],
        "image_info": {"width": w, "height": h, "mode": "BGRâ†’Grayscale", "size_kb": round(w*h*3/1024,1)},
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
        "description": f"Dua gambar digabungkan dengan Î±={alpha} dan (1-Î±)={(1-alpha):.2f}.",
        "steps": [f"Î±={alpha}", f"Piksel img1[0,0]: {p1}", f"Piksel img2[0,0]: {p2}", f"Output â‰ˆ {[round(alpha*a+(1-alpha)*b) for a,b in zip(p1,p2)]}"],
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
        "description": "Background (Gaussian blur 51Ã—51) dikurangi dari gambar asli.",
        "steps": ["B(x,y) = GaussianBlur(f, 51Ã—51)", f"Piksel asli[10,10]: {p1}", f"Background[10,10]: {p2}", f"D = {[abs(int(a)-int(b)) for a,b in zip(p1,p2)]}"],
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
        "steps": ["Nilai piksel f1 Ã— f2", "Dibagi 255 untuk mencegah overflow", "Piksel hitam di img2 â†’ area jadi hitam total"],
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
        "steps": ["Piksel 0 di img2 â†’ diganti 1 agar tidak error (ZeroDivision)", "f1 Ã· f2 Ã— 255", "Area gelap akibat bayangan bisa kembali normal"],
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
        "description": f"Rotasi {angle}Â° terhadap pusat ({cx},{cy}).",
        "steps": [f"Î¸={angle}Â°, cosÎ¸={round(math.cos(rad),4)}, sinÎ¸={round(math.sin(rad),4)}", f"Pusat: ({cx},{cy})"],
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
        "steps": [f"Asli: {w}Ã—{h}", f"Baru: {nw}Ã—{nh}", "Interpolasi bilinear untuk mengisi piksel."],
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
        "steps": [f"M = [[1,0,{tx}],[0,1,{ty}]]", f"Piksel (50,30) â†’ ({50+tx},{30+ty})"],
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
        "description": f"Î²={beta} ditambahkan ke setiap piksel.",
        "steps": [f"Î²={beta}", f"Piksel[0,0]B: {p}", f"g={p}+{beta}={p+beta}", f"Clipâ†’{po}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_contrast(img, params):
    alpha=float(params.get("alpha",1.5)); result=cv2.convertScaleAbs(img,alpha=alpha,beta=0)
    p=int(img[0,0,0]); po=min(255,max(0,int(alpha*p)))
    return {"result": result, "explanation": {
        "title": "Contrast (Kontras)",
        "formula": r"g(x,y) = \text{clip}(\alpha \cdot f(x,y),\;0,\;255)",
        "description": f"Î±={alpha}. Î±>1 meningkatkan, Î±<1 mengurangi kontras.",
        "steps": [f"Î±={alpha}", f"Piksel[0,0]B: {p}", f"g={alpha}Ã—{p}={round(alpha*p,2)}", f"Clipâ†’{po}"],
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
        "title": f"Mean Filter ({ksize}Ã—{ksize})",
        "formula": r"g(x,y) = \frac{1}{k^2}\sum_{m,n \in W} f(x+m, y+n)",
        "description": f"Rata-rata {ksize}Ã—{ksize}={ksize*ksize} tetangga. Mengurangi noise acak.",
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
        "title": f"Median Filter ({ksize}Ã—{ksize})",
        "formula": r"g(x,y) = \text{median}\{f(x+m, y+n) \;|\; m,n \in W\}",
        "description": f"Median dari {ksize}Ã—{ksize} tetangga. Efektif untuk salt-and-pepper noise.",
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
        "steps": ["Kernel Sobel dikonvolusi dengan gambar grayscale", "Magnitude = âˆš(GxÂ²+GyÂ²)"],
    }}

def op_enhance_pipeline(img, params):
    beta=int(params.get("beta",30)); alpha=float(params.get("alpha",1.3))
    s1=cv2.convertScaleAbs(img,alpha=1.0,beta=beta); s2=cv2.convertScaleAbs(s1,alpha=alpha,beta=0)
    blur=cv2.GaussianBlur(s2,(0,0),3); s3=cv2.addWeighted(s2,1.5,blur,-0.5,0)
    result=cv2.medianBlur(s3,3)
    return {"result": result, "explanation": {
        "title": "Enhancement Pipeline",
        "formula": r"g=\text{Median}(\text{Sharpen}(\alpha\cdot(f+\beta)))",
        "description": "Pipeline: Brightnessâ†’Contrastâ†’Sharpeningâ†’Denoising.",
        "steps": [f"1. Brightness: gâ‚=f+{beta}", f"2. Contrast: gâ‚‚={alpha}Ã—gâ‚", "3. Unsharp Mask: gâ‚ƒ=1.5Ã—gâ‚‚âˆ’0.5Ã—Blur", "4. Median: gâ‚„=Median(gâ‚ƒ,3)"],
        "pipeline": [{"name":"Original","beta":0,"alpha":1.0},{"name":"+Brightness","beta":beta,"alpha":1.0},{"name":"+Contrast","beta":beta,"alpha":alpha},{"name":"+Sharpen+Denoise","beta":beta,"alpha":alpha}],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}


def op_saturation(img, params):
    """
    Saturasi: ubah kejenuhan warna via ruang HSV
    s > 0  â†’ warna lebih jenuh/vivid
    s < 0  â†’ warna memudar (menuju grayscale)
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
            "Ruang warna dikonversi BGRâ†’HSV, channel S (kejenuhan) dimodifikasi, lalu dikembalikan ke BGR. "
            "s=+100 menggandakan saturasi, s=-100 â†’ gambar grayscale."
        ),
        "steps": [
            "1. BGR â†’ HSV  (Hue: 0-180Â°, Saturation: 0-255, Value: 0-255)",
            f"   scale = 1 + {s_factor}/100 = {round(scale,2)}",
            f"2. Piksel [0,0] HSV asli: H={p_h}, S={p_s}, V={p_v}",
            f"3. S' = clip({p_s} Ã— {round(scale,2)}, 0, 255) = {p_s_new}",
            "4. HSV â†’ BGR  (konversi kembali ke format display)",
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
            f"Hue digeser {shift}Â°. Roda warna diputar: merahâ†’kuningâ†’hijauâ†’biruâ†’unguâ†’merah. "
            "OpenCV menggunakan rentang H: 0-180 (bukan 0-360)."
        ),
        "steps": [
            "1. BGR â†’ HSV",
            f"   Î”h = {shift}Â° â†’ dalam OpenCV = {shift//2} (skala Â½)",
            f"2. Piksel [0,0] Hue asli: {p_h} (={p_h*2}Â° aktual)",
            f"3. H' = ({p_h} + {shift//2}) mod 180 = {p_h_new}",
            "4. HSV â†’ BGR",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_sharpness(img, params):
    """
    Sharpness via Unsharp Masking:
    g = clip(img + amount Ã— (img - GaussianBlur(img)))
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
        "title": "Sharpness (Ketajaman) â€” Unsharp Masking",
        "formula": r"g(x,y) = \text{clip}(f(x,y) + a \cdot (f(x,y) - \text{Blur}(f(x,y))),\;0,\;255)",
        "description": (
            f"Unsharp Masking dengan amount={amount}. "
            "Blur dikurangi dari asli menghasilkan 'detail mask'. "
            "Detail mask ditambahkan kembali ke gambar asli."
        ),
        "steps": [
            "1. Buat blur: B = GaussianBlur(f, sigma=2)",
            f"   Amount a = {amount}",
            "2. Hitung detail mask: D = f âˆ’ B",
            "3. Tambah ke asli: g = f + a Ã— D",
            f"4. Piksel [10,10]: f={p_b}, B={p_blur}, D={p_b-p_blur}",
            f"   g = {p_b} + {amount}Ã—{p_b-p_blur} = {p_sharp}",
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
        "title": f"Gaussian Blur (Ïƒ={sigma})",
        "formula": r"G(x,y) = \frac{1}{2\pi\sigma^2} e^{-\frac{x^2+y^2}{2\sigma^2}}",
        "description": (
            f"Gaussian Blur dengan Ïƒ={sigma}, kernel {ksize}Ã—{ksize}. "
            "Piksel lebih dekat ke pusat mendapat bobot lebih besar (distribusi normal). "
            "Lebih halus dari Mean Filter karena tidak memotong frekuensi secara tiba-tiba."
        ),
        "kernel": kernel_show[:min(5, ksize)],
        "steps": [
            f"Ïƒ = {sigma}, ksize = {ksize}Ã—{ksize}",
            f"G(0,0) = 1/(2Ï€Ã—{sigma}Â²) Ã— e^0 â†’ bobot terbesar di pusat",
            f"G(1,0) â‰ˆ e^(-1/(2Ã—{sigma}Â²)) Ã— bobot pusat",
            "Total semua bobot = 1.0 (normalized)",
            "Setiap piksel = Î£(kernel Ã— tetangga)",
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
            f"Î± = {opacity_val}/100 = {alpha}",
            f"Background B = {'putih (255,255,255)' if bg_color=='white' else 'hitam (0,0,0)'}",
            f"Piksel [0,0] asli: {p}",
            f"g = {alpha}Ã—{p} + {1-alpha:.2f}Ã—{bg_p}",
            f"g â‰ˆ {p_out}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_morphology(img, params):
    mode = params.get("mode", "dilation")
    source = params.get("source", "binary")
    ksize = max(3, int(params.get("ksize", 5)))
    if ksize % 2 == 0:
        ksize += 1
    iterations = max(1, min(int(params.get("iterations", 1)), 8))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if source == "binary":
        _, base = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif source == "grayscale":
        base = gray
    else:
        base = img

    if mode == "erosion":
        result = cv2.erode(base, kernel, iterations=iterations)
        formula = "A eroded by B"
        title = "Erosion"
    elif mode == "opening":
        result = cv2.morphologyEx(base, cv2.MORPH_OPEN, kernel, iterations=iterations)
        formula = "(A eroded by B) dilated by B"
        title = "Opening"
    elif mode == "closing":
        result = cv2.morphologyEx(base, cv2.MORPH_CLOSE, kernel, iterations=iterations)
        formula = "(A dilated by B) eroded by B"
        title = "Closing"
    elif mode == "boundary":
        eroded = cv2.erode(base, kernel, iterations=iterations)
        result = cv2.subtract(base, eroded)
        formula = "Boundary(A) = A - erosion(A)"
        title = "Boundary Extraction"
    else:
        result = cv2.dilate(base, kernel, iterations=iterations)
        formula = "A dilated by B"
        title = "Dilation"

    result_bgr = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR) if len(result.shape) == 2 else result
    return {"result": result_bgr, "explanation": {
        "title": title,
        "formula": formula,
        "description": f"Morphology memakai structuring element {ksize}x{ksize} selama {iterations} iterasi.",
        "steps": [
            f"Source: {source}",
            f"Mode: {mode}",
            f"Kernel: rectangle {ksize}x{ksize}",
            f"Iterations: {iterations}",
        ],
        "kernel": kernel.tolist(),
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result_bgr),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result_bgr),
    }}


def zhang_suen_thinning(binary: np.ndarray, max_iterations: int = 80) -> np.ndarray:
    img_bin = (binary > 0).astype(np.uint8)
    changed = True
    iteration = 0
    while changed and iteration < max_iterations:
        changed = False
        to_remove = []
        rows, cols = img_bin.shape
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                if img_bin[i, j] != 1:
                    continue
                p2 = img_bin[i - 1, j]
                p3 = img_bin[i - 1, j + 1]
                p4 = img_bin[i, j + 1]
                p5 = img_bin[i + 1, j + 1]
                p6 = img_bin[i + 1, j]
                p7 = img_bin[i + 1, j - 1]
                p8 = img_bin[i, j - 1]
                p9 = img_bin[i - 1, j - 1]
                neighbors = [p2, p3, p4, p5, p6, p7, p8, p9]
                n = sum(neighbors)
                transitions = sum((neighbors[k] == 0 and neighbors[(k + 1) % 8] == 1) for k in range(8))
                if 2 <= n <= 6 and transitions == 1 and p2 * p4 * p6 == 0 and p4 * p6 * p8 == 0:
                    to_remove.append((i, j))
        if to_remove:
            changed = True
            for i, j in to_remove:
                img_bin[i, j] = 0

        to_remove = []
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                if img_bin[i, j] != 1:
                    continue
                p2 = img_bin[i - 1, j]
                p3 = img_bin[i - 1, j + 1]
                p4 = img_bin[i, j + 1]
                p5 = img_bin[i + 1, j + 1]
                p6 = img_bin[i + 1, j]
                p7 = img_bin[i + 1, j - 1]
                p8 = img_bin[i, j - 1]
                p9 = img_bin[i - 1, j - 1]
                neighbors = [p2, p3, p4, p5, p6, p7, p8, p9]
                n = sum(neighbors)
                transitions = sum((neighbors[k] == 0 and neighbors[(k + 1) % 8] == 1) for k in range(8))
                if 2 <= n <= 6 and transitions == 1 and p2 * p4 * p8 == 0 and p2 * p6 * p8 == 0:
                    to_remove.append((i, j))
        if to_remove:
            changed = True
            for i, j in to_remove:
                img_bin[i, j] = 0
        iteration += 1
    return (img_bin * 255).astype(np.uint8)


def op_zhang_suen(img, params):
    invert = bool(params.get("invert", False))
    max_dim = int(params.get("max_dim", 900))
    max_iterations = int(params.get("max_iterations", 80))
    h, w = img.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    work = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else img.copy()
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, 0, 255, thresh_type + cv2.THRESH_OTSU)
    skeleton = zhang_suen_thinning(binary, max_iterations=max_iterations)
    result = cv2.cvtColor(skeleton, cv2.COLOR_GRAY2BGR)
    return {"result": result, "explanation": {
        "title": "Zhang-Suen Thinning",
        "formula": "Two sub-iterations remove safe boundary pixels until stable",
        "description": "Penipisan objek menjadi skeleton satu piksel tanpa menghilangkan struktur utama.",
        "steps": [
            "Konversi grayscale",
            "Binarisasi Otsu",
            "Sub-iterasi 1 menghapus piksel batas yang memenuhi syarat",
            "Sub-iterasi 2 menghapus piksel batas arah komplementer",
            f"Berhenti saat stabil atau mencapai {max_iterations} iterasi",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_edge_detection(img, params):
    method = params.get("method", "canny")
    blur_size = max(1, int(params.get("blur", 3)))
    if blur_size % 2 == 0:
        blur_size += 1
    low = int(params.get("low", 60))
    high = int(params.get("high", 160))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (blur_size, blur_size), 0) if blur_size > 1 else gray

    if method == "sobel":
        gx = cv2.Sobel(smooth, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(smooth, cv2.CV_64F, 0, 1, ksize=3)
        edge = cv2.convertScaleAbs(cv2.magnitude(gx, gy))
        formula = "G = sqrt(Gx^2 + Gy^2)"
    elif method == "prewitt":
        kx = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
        ky = np.array([[1, 1, 1], [0, 0, 0], [-1, -1, -1]], dtype=np.float32)
        gx = cv2.filter2D(smooth, cv2.CV_32F, kx)
        gy = cv2.filter2D(smooth, cv2.CV_32F, ky)
        edge = cv2.convertScaleAbs(cv2.magnitude(gx, gy))
        formula = "Prewitt gradient magnitude"
    elif method == "roberts":
        kx = np.array([[1, 0], [0, -1]], dtype=np.float32)
        ky = np.array([[0, 1], [-1, 0]], dtype=np.float32)
        gx = cv2.filter2D(smooth, cv2.CV_32F, kx)
        gy = cv2.filter2D(smooth, cv2.CV_32F, ky)
        edge = cv2.convertScaleAbs(cv2.magnitude(gx, gy))
        formula = "Roberts diagonal gradient"
    elif method == "laplacian":
        edge = cv2.convertScaleAbs(cv2.Laplacian(smooth, cv2.CV_64F))
        formula = "Laplacian second derivative"
    else:
        edge = cv2.Canny(smooth, low, high)
        formula = f"Canny hysteresis threshold: low={low}, high={high}"

    result = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)
    return {"result": result, "explanation": {
        "title": f"Edge Detection - {method.title()}",
        "formula": formula,
        "description": "Deteksi tepi menandai perubahan intensitas yang tajam sebagai batas region atau objek.",
        "steps": [
            "Konversi ke grayscale",
            f"Smoothing Gaussian blur {blur_size}x{blur_size}",
            f"Metode: {method}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_segmentation(img, params):
    mode = params.get("mode", "otsu_blur")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if mode == "global_binary":
        threshold = int(params.get("threshold", 127))
        _, segmented = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        formula = f"g=255 if f >= {threshold}, else 0"
    elif mode == "adaptive_gaussian":
        block_size = max(3, int(params.get("block_size", 21)))
        if block_size % 2 == 0:
            block_size += 1
        c_value = int(params.get("c", 5))
        segmented = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c_value)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        formula = f"local threshold = weighted mean({block_size}x{block_size}) - {c_value}"
    elif mode == "kmeans":
        clusters = max(2, min(int(params.get("clusters", 4)), 8))
        data = img.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        centers = np.uint8(centers)
        result = centers[labels.flatten()].reshape(img.shape)
        formula = f"K-Means clustering with K={clusters}"
    else:
        blur_size = max(3, int(params.get("blur", 5)))
        if blur_size % 2 == 0:
            blur_size += 1
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        otsu_value, segmented = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        formula = f"Otsu threshold T={round(float(otsu_value), 2)} after Gaussian blur {blur_size}x{blur_size}"

    return {"result": result, "explanation": {
        "title": "Segmentasi Citra",
        "formula": formula,
        "description": "Segmentasi memisahkan citra menjadi region berdasarkan intensitas atau kemiripan warna.",
        "steps": [
            f"Mode: {mode}",
            "Output menandai region/cluster yang memenuhi kriteria segmentasi",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# OPERATIONS ROUTER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
    "morphology":       op_morphology,
    "zhang_suen":       op_zhang_suen,
    "edge_detection":   op_edge_detection,
    "segmentation":     op_segmentation,
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

    # â”€â”€ TAHAP 1: Bilateral Filtering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    denoised = cv2.bilateralFilter(work, d=9, sigmaColor=75, sigmaSpace=75)
    stages.append({
        "id": "bilateral", "order": 1,
        "title": "Bilateral Filtering",
        "objective": "Mengurangi noise sambil mempertahankan ketajaman tepi objek (edge-preserving smoothing).",
        "formula": r"BF[I]_p=\frac{1}{W_p}\sum_{q\in S} I_q\, f_r(\|I_p-I_q\|)\, g_s(\|p-q\|)",
        "math_concept": (
            "Menggabungkan dua kernel Gaussian: kernel spasial g_s (berdasarkan jarak piksel) dan kernel "
            "range f_r (berdasarkan perbedaan intensitas). Piksel tetangga yang nilainya jauh berbeda "
            "(kemungkinan besar tepi objek) diberi bobot kecil â€” sehingga noise berkurang tanpa mengaburkan tepi, "
            "berbeda dari Gaussian Blur biasa yang mengaburkan segalanya secara merata."
        ),
        "description": "Parameter: d=9 (diameter neighborhood), sigmaColor=75, sigmaSpace=75.",
        "image": encode_stage_preview(denoised),
    })

    # â”€â”€ TAHAP 2: CLAHE pada channel L (Lab) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            "CLAHE membagi channel L menjadi blok 8Ã—8, melakukan ekualisasi histogram per-blok dengan batas "
            "klip (clipLimit=3.0) untuk mencegah over-amplifikasi noise, lalu interpolasi bilinear antar blok "
            "agar transisi mulus. Channel warna (a,b) tidak disentuh sehingga warna asli tetap akurat."
        ),
        "description": "Diterapkan hanya pada channel L (Lightness), bukan ke seluruh citra BGR.",
        "image": encode_stage_preview(enhanced),
    })

    # â”€â”€ TAHAP 3: GrabCut (segmentasi awal) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ TAHAP 4: Morphological Opening â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(grabcut_mask, cv2.MORPH_OPEN, k_open, iterations=2)
    stages.append({
        "id": "opening", "order": 4,
        "title": "Morphological Opening",
        "objective": "Menghapus bintik/noise kecil yang salah terdeteksi sebagai bagian foreground.",
        "formula": r"A \circ B = (A \ominus B) \oplus B",
        "math_concept": (
            "Operasi Erosi (mengikis tepi region) diikuti Dilasi (melebarkan kembali), menggunakan elemen "
            "struktur elips 5Ã—5. Objek yang lebih sempit dari elemen struktur akan hilang total, sedangkan "
            "objek utama yang cukup besar bentuknya tetap dipertahankan."
        ),
        "description": "Structuring element: ellipse 5Ã—5, 2 iterasi.",
        "image": encode_stage_preview(opened),
    })

    # â”€â”€ TAHAP 5: Morphological Closing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, k_close, iterations=2)
    stages.append({
        "id": "closing", "order": 5,
        "title": "Morphological Closing",
        "objective": "Menutup lubang-lubang kecil di dalam area objek agar mask menjadi solid/utuh.",
        "formula": r"A \bullet B = (A \oplus B) \ominus B",
        "math_concept": (
            "Kebalikan dari Opening: Dilasi diikuti Erosi, menggunakan elemen struktur elips 9Ã—9 (lebih besar "
            "agar mampu menutup celah yang lebih lebar). Lubang atau celah yang lebih kecil dari elemen "
            "struktur akan tertutup tanpa mengubah ukuran objek secara keseluruhan."
        ),
        "description": "Structuring element: ellipse 9Ã—9, 2 iterasi.",
        "image": encode_stage_preview(closed),
    })

    # â”€â”€ TAHAP 6: Distance Transform + Watershed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ TAHAP 7: Sobel + Laplacian Edge Fusion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ TAHAP 8: Contour Optimization + Connected Component Analysis â”€â”€
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
        "description": f"{max(0,num_labels-1)} komponen ditemukan, {kept} dipertahankan (area â‰¥ 0.5% dari citra).",
        "image": encode_stage_preview(cca_mask),
    })

    # â”€â”€ TAHAP 9: Alpha Matting + Gaussian Feathering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            "(B) sesuai nilai alpha âˆˆ [0,1]. Alpha dibangun dari Distance Transform (jarak ke tepi mask, "
            "dinormalisasi dalam band 8px) lalu dihaluskan dengan Gaussian Blur agar transisi lembut."
        ),
        "description": "Band transisi 8px, Gaussian kernel 9Ã—9 Ïƒ=2.0.",
        "image": encode_stage_preview(alpha_final),
    })

    # â”€â”€ Upscale alpha ke resolusi asli & komposit hasil akhir â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        "work_resolution": f"{ww}Ã—{wh}",
        "original_resolution": f"{ow}Ã—{oh}",
    }



def order_points(pts: np.ndarray) -> np.ndarray:
    """Urutkan 4 titik sudut menjadi [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]          # top-left  â†’ jumlah x+y terkecil
    rect[2] = pts[np.argmax(s)]          # bottom-right â†’ jumlah x+y terbesar
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]       # top-right â†’ selisih x-y terkecil
    rect[3] = pts[np.argmax(diff)]       # bottom-left â†’ selisih x-y terbesar
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray, target_aspect: float | None = None):
    """Warp a 4-point document region into a top-down rectangle."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b), 10)

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b), 10)

    if target_aspect and target_aspect > 0:
        aspect = target_aspect if max_w >= max_h else 1.0 / target_aspect
        if max_w / max_h > aspect:
            max_h = max(10, int(max_w / aspect))
        else:
            max_w = max(10, int(max_h * aspect))

    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, matrix, (max_w, max_h))
    return warped, matrix, max_w, max_h


def get_paper_aspect(paper_size: str) -> float | None:
    if paper_size == "a4":
        return 1.41421356237
    if paper_size == "letter":
        return 11 / 8.5
    if paper_size == "id":
        return 85.6 / 53.98
    return None


def quad_aspect_ratio(pts: np.ndarray) -> float:
    rect = order_points(pts.astype(np.float32))
    width = max(np.linalg.norm(rect[2] - rect[3]), np.linalg.norm(rect[1] - rect[0]))
    height = max(np.linalg.norm(rect[1] - rect[2]), np.linalg.norm(rect[0] - rect[3]))
    if min(width, height) <= 0:
        return 0.0
    return max(width, height) / min(width, height)


def remove_tiny_dark_components(binary_white_bg: np.ndarray, min_area: int = 8) -> np.ndarray:
    """Remove isolated black specks from a black-text-on-white binary document."""
    inverted = cv2.bitwise_not(binary_white_bg)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(inverted, connectivity=8)
    cleaned = inverted.copy()
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        if area <= min_area or (width <= 2 and height <= 2):
            cleaned[labels == label] = 0
    return cv2.bitwise_not(cleaned)


def find_document_quad(work: np.ndarray, auto_crop: bool = True):
    """Find the strongest 4-corner document candidate in a resized work image."""
    wh, ww = work.shape[:2]
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    if not auto_crop:
        edges = cv2.Canny(blur, 50, 150)
        contour_vis = work.copy()
        cv2.putText(
            contour_vis,
            "Auto-crop off - full frame",
            (10, wh - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (80, 220, 120),
            1,
            cv2.LINE_AA,
        )
        return None, contour_vis, edges, blur, 0.0

    median = float(np.median(blur))
    lower = int(max(25, 0.66 * median))
    upper = int(min(220, 1.33 * median + 35))
    edges = cv2.Canny(blur, lower, upper)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    edge_map = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    edge_map = cv2.dilate(edge_map, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:12]

    quad = None
    best_score = 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 0.08 * wh * ww:
            continue
        perimeter = cv2.arcLength(contour, True)
        for epsilon in (0.015, 0.02, 0.03, 0.04):
            approx = cv2.approxPolyDP(contour, epsilon * perimeter, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            pts = approx.reshape(4, 2).astype(np.float32)
            rect = order_points(pts)
            width = max(np.linalg.norm(rect[2] - rect[3]), np.linalg.norm(rect[1] - rect[0]))
            height = max(np.linalg.norm(rect[1] - rect[2]), np.linalg.norm(rect[0] - rect[3]))
            if width < 40 or height < 40:
                continue
            area_ratio = area / float(wh * ww)
            rectangularity = min(1.0, area / max(width * height, 1.0))
            edge_margin = min(
                rect[:, 0].min(),
                rect[:, 1].min(),
                ww - rect[:, 0].max(),
                wh - rect[:, 1].max(),
            )
            margin_bonus = 1.0 if edge_margin > -8 else 0.7
            score = area_ratio * 0.65 + rectangularity * 0.30 + margin_bonus * 0.05
            if score > best_score:
                best_score = score
                quad = pts

    if quad is None and contours and cv2.contourArea(contours[0]) > 0.10 * wh * ww:
        rect = cv2.minAreaRect(contours[0])
        candidate = cv2.boxPoints(rect).astype(np.float32)
        box_area = cv2.contourArea(candidate)
        if box_area > 0.10 * wh * ww:
            quad = candidate
            best_score = min(0.75, box_area / float(wh * ww))

    contour_vis = work.copy()
    safe_quad = quad is not None and best_score >= 0.80

    if quad is not None and safe_quad:
        cv2.drawContours(contour_vis, [quad.astype(int)], -1, (80, 220, 120), 3)
        for x, y in quad:
            cv2.circle(contour_vis, (int(x), int(y)), 6, (80, 220, 120), -1)
    elif quad is not None:
        cv2.drawContours(contour_vis, [quad.astype(int)], -1, (80, 180, 255), 2)
        cv2.putText(
            contour_vis,
            "Weak document geometry - full frame used",
            (10, wh - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (80, 180, 255),
            1,
            cv2.LINE_AA,
        )
        quad = None
    else:
        cv2.putText(
            contour_vis,
            "Document edge not detected - full frame used",
            (10, wh - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (80, 220, 120),
            1,
            cv2.LINE_AA,
        )

    return quad, contour_vis, edge_map, blur, round(float(best_score), 3)


def run_document_scan_pipeline(original: np.ndarray, options: dict | None = None, work_max_dim: int = 1100) -> dict:
    """Document scanner pipeline with auto-crop, deskew, cleanup, and scan modes."""
    options = options or {}
    preset = str(options.get("preset", "document"))
    enhance = str(options.get("enhance", "balanced"))
    auto_crop = bool(options.get("auto_crop", True))
    paper_size = str(options.get("paper_size", "auto"))
    output_max = int(options.get("output_max", 1800))
    output_max = max(900, min(output_max, 2600))

    if preset == "id":
        paper_size = "id"
    elif preset == "receipt":
        paper_size = "auto"

    strength_map = {
        "soft": {"denoise": 6, "sharp_gray": 1.25, "sharp_color": 1.15, "clahe": 1.6, "block": 31, "c": 8, "speck": 4},
        "balanced": {"denoise": 9, "sharp_gray": 1.45, "sharp_color": 1.25, "clahe": 2.1, "block": 31, "c": 10, "speck": 7},
        "strong": {"denoise": 12, "sharp_gray": 1.70, "sharp_color": 1.35, "clahe": 2.8, "block": 35, "c": 12, "speck": 10},
    }
    cfg = strength_map.get(enhance, strength_map["balanced"])

    oh, ow = original.shape[:2]
    scale = min(1.0, work_max_dim / max(oh, ow))
    work = cv2.resize(
        original,
        (max(1, int(ow * scale)), max(1, int(oh * scale))),
        interpolation=cv2.INTER_AREA,
    ) if scale < 1.0 else original.copy()

    stages = []
    quad, contour_vis, edge_map, blur, detection_score = find_document_quad(work, auto_crop=auto_crop)

    stages.append({
        "id": "preprocess",
        "order": 1,
        "title": "Grayscale + Gaussian Blur",
        "objective": "Menyederhanakan citra ke satu channel dan meredam noise sebelum deteksi tepi.",
        "formula": r"L=0.299R+0.587G+0.114B,\quad B=G_{\sigma}*L",
        "math_concept": "Citra dikonversi ke grayscale agar deteksi tepi tidak terganggu variasi warna. Gaussian blur 5x5 meredam tekstur kertas dan noise kamera sebelum Canny.",
        "description": "Gaussian kernel 5x5, sigma otomatis dari OpenCV.",
        "image": encode_stage_preview(blur),
    })

    stages.append({
        "id": "edges",
        "order": 2,
        "title": "Adaptive Canny Edge Detection",
        "objective": "Menemukan batas dokumen secara lebih stabil pada foto terang, gelap, atau kontras rendah.",
        "formula": r"G=\sqrt{G_x^2+G_y^2},\quad T_{low}=0.66m,\quad T_{high}=1.33m+35",
        "math_concept": "Ambang Canny dihitung dari median intensitas gambar, sehingga tidak bergantung pada satu nilai tetap. Morphological closing menyambung celah tepi dokumen yang terputus.",
        "description": "Adaptive threshold Canny + morph close 7x7 + dilate 3x3.",
        "image": encode_stage_preview(edge_map),
    })

    stages.append({
        "id": "contour",
        "order": 3,
        "title": "Contour Scoring + Corner Detection",
        "objective": "Memilih kandidat dokumen terbaik berdasarkan luas, bentuk segiempat, dan konsistensi frame.",
        "formula": r"score=0.65A+0.30R+0.05M",
        "math_concept": "Kontur besar disederhanakan menjadi poligon. Kandidat empat titik dinilai dari area ratio, rectangularity, dan margin. Jika tidak ada kandidat kuat, sistem fallback ke rotated bounding box.",
        "description": f"Document detected: {quad is not None}. Detection score: {detection_score}.",
        "image": encode_stage_preview(contour_vis),
    })

    warp_note = "full frame fallback"
    if quad is not None:
        pts_full = quad / scale
        requested_aspect = get_paper_aspect(paper_size)
        detected_aspect = quad_aspect_ratio(pts_full)
        target_aspect = requested_aspect
        if requested_aspect and detected_aspect > 0:
            aspect_error = abs(detected_aspect - requested_aspect) / requested_aspect
            if aspect_error > 0.08:
                target_aspect = None
                warp_note = f"kept detected aspect ({detected_aspect:.2f}) because {paper_size} would stretch it"
            else:
                warp_note = f"normalized to {paper_size} aspect"
        elif requested_aspect is None:
            warp_note = "kept detected aspect"

        warped_color, _, mw, mh = four_point_transform(original, pts_full, target_aspect)
        doc_detected = True
    else:
        warped_color, mw, mh = original.copy(), ow, oh
        doc_detected = False

    proc_scale = min(1.0, output_max / max(mw, mh))
    if proc_scale < 1.0:
        warped_color = cv2.resize(
            warped_color,
            (int(mw * proc_scale), int(mh * proc_scale)),
            interpolation=cv2.INTER_AREA,
        )

    stages.append({
        "id": "perspective",
        "order": 4,
        "title": "Perspective Correction + Auto Crop",
        "objective": "Meluruskan foto dokumen yang miring agar terlihat seperti hasil scan datar.",
        "formula": r"p'=Hp,\quad H=\text{getPerspectiveTransform}(src_4,dst_4)",
        "math_concept": "Homography 3x3 memetakan empat sudut dokumen ke rectangle baru. Ini memperbaiki distorsi perspektif saat dokumen difoto dari sudut miring.",
        "description": f"Output before cap: {mw}x{mh}px. Paper mode: {paper_size}. Auto-crop: {auto_crop}. {warp_note}.",
        "image": encode_stage_preview(warped_color),
    })

    warped_gray = cv2.cvtColor(warped_color, cv2.COLOR_BGR2GRAY)

    bg_kernel = max(31, (min(warped_gray.shape[:2]) // 18) | 1)
    bg_estimate = cv2.medianBlur(cv2.dilate(warped_gray, np.ones((9, 9), np.uint8)), bg_kernel)
    shadow_removed = cv2.divide(warped_gray, bg_estimate, scale=255)
    shadow_removed = cv2.normalize(shadow_removed, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    lab = cv2.cvtColor(warped_color, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    l_bg = cv2.medianBlur(cv2.dilate(l_ch, np.ones((9, 9), np.uint8)), bg_kernel)
    l_corrected = cv2.divide(l_ch, l_bg, scale=255)
    l_corrected = cv2.normalize(l_corrected, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    color_shadow_fixed = cv2.cvtColor(cv2.merge([l_corrected, a_ch, b_ch]), cv2.COLOR_LAB2BGR)

    stages.append({
        "id": "illumination",
        "order": 5,
        "title": "Shadow and Stain Normalization",
        "objective": "Meratakan pencahayaan, mengurangi bayangan, dan membuat area kertas lebih bersih.",
        "formula": r"B=\text{median}(\text{dilate}(I)),\quad I'=\frac{I}{B}\times255",
        "math_concept": "Background estimation membuat peta pencahayaan lokal. Pembagian I/B menekan bayangan dan noda lembut tanpa menghapus teks gelap.",
        "description": f"Background kernel {bg_kernel}, enhancement preset: {enhance}.",
        "image": encode_stage_preview(shadow_removed),
    })

    denoised_gray = cv2.fastNlMeansDenoising(
        shadow_removed,
        h=int(cfg["denoise"]),
        templateWindowSize=7,
        searchWindowSize=21,
    )
    denoised_color = cv2.bilateralFilter(color_shadow_fixed, d=7, sigmaColor=50, sigmaSpace=50)

    stages.append({
        "id": "denoise",
        "order": 6,
        "title": "Text-Preserving Noise Reduction",
        "objective": "Membersihkan bintik noise tanpa membuat tepi huruf terlalu lembek.",
        "formula": r"NL[I]_p=\frac{1}{Z_p}\sum w(p,q)I_q",
        "math_concept": "Non-Local Means membandingkan patch yang mirip di seluruh gambar. Noise kecil berkurang, sementara pola teks yang konsisten tetap dipertahankan.",
        "description": f"fastNlMeansDenoising h={int(cfg['denoise'])}. Color path uses bilateral filtering.",
        "image": encode_stage_preview(denoised_gray),
    })

    blur_gray = cv2.GaussianBlur(denoised_gray, (0, 0), 2)
    amount_gray = float(cfg["sharp_gray"])
    sharpened_gray = cv2.convertScaleAbs(cv2.addWeighted(denoised_gray, amount_gray, blur_gray, 1.0 - amount_gray, 0))

    blur_color = cv2.GaussianBlur(denoised_color, (0, 0), 2)
    amount_color = float(cfg["sharp_color"])
    sharpened_color = cv2.convertScaleAbs(cv2.addWeighted(denoised_color, amount_color, blur_color, 1.0 - amount_color, 0))

    stages.append({
        "id": "sharpen",
        "order": 7,
        "title": "Text Sharpening",
        "objective": "Mempertegas huruf, garis tabel, dan tanda tangan setelah noise reduction.",
        "formula": r"g=f+a(f-\text{Blur}(f))",
        "math_concept": "Unsharp masking mengambil detail dari selisih gambar asli dan gambar blur, lalu menambahkannya kembali untuk memperjelas tepi teks.",
        "description": f"Gray amount={amount_gray}, color amount={amount_color}, sigma=2.",
        "image": encode_stage_preview(sharpened_gray),
    })

    block_size = int(cfg["block"])
    if block_size % 2 == 0:
        block_size += 1

    bw = cv2.adaptiveThreshold(
        sharpened_gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        int(cfg["c"]),
    )
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1)
    bw = remove_tiny_dark_components(bw, min_area=int(cfg["speck"]))

    clean = cv2.adaptiveThreshold(
        sharpened_gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        block_size,
        max(6, int(cfg["c"]) - 2),
    )
    clean = remove_tiny_dark_components(clean, min_area=max(4, int(cfg["speck"]) - 2))

    clahe = cv2.createCLAHE(clipLimit=float(cfg["clahe"]), tileGridSize=(8, 8))
    grayscale_mode = clahe.apply(sharpened_gray)

    lab2 = cv2.cvtColor(sharpened_color, cv2.COLOR_BGR2LAB)
    l2, a2, b2 = cv2.split(lab2)
    color_mode = cv2.cvtColor(cv2.merge([clahe.apply(l2), a2, b2]), cv2.COLOR_LAB2BGR)

    stages.append({
        "id": "outputs",
        "order": 8,
        "title": "Scanner Output Modes",
        "objective": "Menghasilkan beberapa mode scan: hitam-putih tegas, clean text, grayscale, dan warna enhanced.",
        "formula": r"g(x,y)=255\;\text{if}\;f(x,y)>T_{local}(x,y)-C",
        "math_concept": "Adaptive threshold menghitung ambang lokal per area sehingga teks tetap terbaca saat pencahayaan tidak rata. CLAHE dipakai untuk mode grayscale dan warna agar kontras naik tanpa binerisasi.",
        "description": f"blockSize={block_size}, C={int(cfg['c'])}, CLAHE clipLimit={float(cfg['clahe'])}.",
        "image": encode_stage_preview(bw),
        "secondary_image": encode_stage_preview(color_mode),
    })

    hist_before = get_histogram(original)
    hist_after = get_histogram(cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR))

    return {
        "grayscale": encode_image(cv2.cvtColor(grayscale_mode, cv2.COLOR_GRAY2BGR)),
        "bw": encode_image(cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)),
        "clean": encode_image(cv2.cvtColor(clean, cv2.COLOR_GRAY2BGR)),
        "color": encode_image(color_mode),
        "stages": stages,
        "doc_detected": doc_detected,
        "detection_score": detection_score,
        "output_resolution": f"{sharpened_gray.shape[1]}x{sharpened_gray.shape[0]}",
        "histogram_before": hist_before,
        "histogram_after": hist_after,
    }


# ADVANCED EDITOR API ROUTES

@app.route("/api/auth/firebase", methods=["POST"])
@require_firebase_auth
def auth_firebase():
    user = g.user or {}
    return jsonify({
        "ok": True,
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name"),
    })

@app.route("/api/editor/scan-document", methods=["POST"])
@require_firebase_auth
def editor_scan_document():
    """Scan and restore a document image with OpenCV."""
    try:
        data = request.get_json()
        img = decode_image(data.get("image"))
        options = data.get("options") or {}
        out = run_document_scan_pipeline(img, options=options)
        return jsonify({
            "grayscale": out["grayscale"],
            "bw": out["bw"],
            "clean": out["clean"],
            "color": out["color"],
            "method": "Document Scanner Pipeline (8 tahap)",
            "stages": out["stages"],
            "doc_detected": out["doc_detected"],
            "detection_score": out["detection_score"],
            "output_resolution": out["output_resolution"],
            "histogram_before": out["histogram_before"],
            "histogram_after": out["histogram_after"],
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/editor/cutout", methods=["POST"])
@require_firebase_auth
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
@require_firebase_auth
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MAIN API ROUTE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@app.route("/api/process", methods=["POST"])
@require_firebase_auth
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

# â”€â”€ Serve React build â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    file_path = os.path.join(FRONTEND_BUILD, path)
    if path and os.path.exists(file_path):
        return send_from_directory(FRONTEND_BUILD, path)
    return send_from_directory(FRONTEND_BUILD, "index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)







