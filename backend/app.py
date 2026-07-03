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


def env_value(*names, default=""):
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(env_value("MAX_CONTENT_LENGTH", "APP_MAX_UPLOAD_BYTES", default=str(16 * 1024 * 1024)))

FRONTEND_URL = env_value("FRONTEND_URL", "PUBLIC_WEB_ORIGIN", default="http://localhost:5173")
cors_default = f"{FRONTEND_URL},http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in env_value("CORS_ORIGINS", "ALLOWED_ORIGINS", default=cors_default).split(",")
    if origin.strip()
]
REQUIRE_AUTH = env_value("REQUIRE_AUTH", "APP_REQUIRE_AUTH", default="true").lower() == "true"
MAX_IMAGE_PIXELS = int(env_value("MAX_IMAGE_PIXELS", "APP_MAX_IMAGE_PIXELS", default="12000000"))
RATE_LIMIT_WINDOW = int(env_value("RATE_LIMIT_WINDOW", "APP_RATE_LIMIT_WINDOW", default="60"))
RATE_LIMIT_MAX = int(env_value("RATE_LIMIT_MAX", "APP_RATE_LIMIT_MAX", default="40"))
SHOW_ERROR_DETAILS = env_value("SHOW_ERROR_DETAILS", "APP_SHOW_ERROR_DETAILS", default="false").lower() == "true"

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
    service_account_json = env_value("FIREBASE_SERVICE_ACCOUNT_JSON", "AUTH_SERVICE_ACCOUNT_JSON")
    service_account_base64 = env_value("FIREBASE_SERVICE_ACCOUNT_BASE64", "AUTH_SERVICE_ACCOUNT_BASE64")
    project_id = env_value("FIREBASE_PROJECT_ID", "AUTH_PROJECT_ID")
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


def internal_error_response(exc):
    app.logger.exception("Unhandled API error: %s", exc)
    payload = {"error": "Terjadi kesalahan saat memproses request."}
    if SHOW_ERROR_DETAILS:
        payload["detail"] = str(exc)
    return jsonify(payload), 500


def clamp_number(value, default, min_value, max_value, cast=float, field="parameter"):
    try:
        number = cast(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} harus berupa angka")
    if isinstance(number, float) and not math.isfinite(number):
        raise ValueError(f"{field} harus berupa angka valid")
    return max(min_value, min(max_value, number))


def int_param(params, name, default, min_value, max_value):
    return int(clamp_number(params.get(name, default), default, min_value, max_value, int, name))


def float_param(params, name, default, min_value, max_value):
    return float(clamp_number(params.get(name, default), default, min_value, max_value, float, name))


def choice_param(params, name, default, allowed):
    value = str(params.get(name, default))
    return value if value in allowed else default


def bool_param(params, name, default=False):
    value = params.get(name, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def ensure_dict(value, field):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} harus berupa object")
    return value


def odd_int(value, min_value, max_value):
    value = max(min_value, min(max_value, int(value)))
    return value if value % 2 == 1 else min(value + 1, max_value if max_value % 2 == 1 else max_value - 1)

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
# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

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


def _gray_uint8(img: np.ndarray) -> np.ndarray:
    img = img.astype(np.uint8) if img.dtype != np.uint8 else img
    return cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img


def get_image_metrics(img: np.ndarray) -> dict:
    """Small, explainable metrics for a pipeline stage preview."""
    gray = _gray_uint8(img)
    h, w = gray.shape[:2]
    edges = cv2.Canny(gray, 70, 170) if h > 1 and w > 1 else np.zeros_like(gray)
    dark_mask = gray < 64
    bright_mask = gray > 220
    ink_mask = gray < 110
    return {
        "width": int(w),
        "height": int(h),
        "channels": int(img.shape[2]) if len(img.shape) == 3 else 1,
        "mean": round(float(np.mean(gray)), 2),
        "std": round(float(np.std(gray)), 2),
        "min": int(np.min(gray)),
        "max": int(np.max(gray)),
        "dark_pct": round(float(np.mean(dark_mask) * 100), 2),
        "bright_pct": round(float(np.mean(bright_mask) * 100), 2),
        "ink_pct": round(float(np.mean(ink_mask) * 100), 2),
        "edge_density_pct": round(float(np.mean(edges > 0) * 100), 2),
    }


def get_pixel_delta_matrix(before: np.ndarray, after: np.ndarray, n=5) -> list:
    before_matrix = np.array(get_pixel_matrix(before, n=n), dtype=np.int16)
    after_matrix = np.array(get_pixel_matrix(after, n=n), dtype=np.int16)
    rows = min(before_matrix.shape[0], after_matrix.shape[0])
    cols = min(before_matrix.shape[1], after_matrix.shape[1])
    if rows == 0 or cols == 0:
        return []
    return (after_matrix[:rows, :cols] - before_matrix[:rows, :cols]).tolist()


def get_stage_changes(before: np.ndarray, after: np.ndarray) -> list:
    before_metrics = get_image_metrics(before)
    after_metrics = get_image_metrics(after)

    def entry(key: str, label: str, unit: str = "", decimals: int = 2) -> dict:
        before_value = before_metrics[key]
        after_value = after_metrics[key]
        delta = round(float(after_value) - float(before_value), decimals)
        return {
            "key": key,
            "label": label,
            "before": before_value,
            "after": after_value,
            "delta": delta,
            "unit": unit,
        }

    return [
        entry("mean", "Rata-rata intensitas"),
        entry("std", "Kontras lokal"),
        entry("dark_pct", "Area gelap", "%"),
        entry("bright_pct", "Area putih/terang", "%"),
        entry("ink_pct", "Estimasi tinta/teks", "%"),
        entry("edge_density_pct", "Kepadatan tepi", "%"),
    ]


def enrich_stage(stage: dict, before: np.ndarray, after: np.ndarray, pixel_source: np.ndarray | None = None) -> dict:
    """Attach per-stage analysis so the frontend can explain what changed."""
    pixel_source = after if pixel_source is None else pixel_source
    stage.update({
        "histogram": get_histogram(after),
        "metrics_before": get_image_metrics(before),
        "metrics_after": get_image_metrics(after),
        "changes": get_stage_changes(before, after),
        "pixel_matrix_before": get_pixel_matrix(before, n=5),
        "pixel_matrix": get_pixel_matrix(pixel_source, n=5),
        "pixel_delta_matrix": get_pixel_delta_matrix(before, pixel_source, n=5),
    })
    return stage

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
    alpha = float_param(params, "alpha", 0.5, 0.0, 1.0)
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
    angle = float_param(params, "angle", 45, -360, 360)
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
    sx=float_param(params, "sx", 1.5, 0.1, 4.0); sy=float_param(params, "sy", 1.5, 0.1, 4.0)
    h,w=img.shape[:2]; nw,nh=max(1,int(w*sx)),max(1,int(h*sy))
    if nw * nh > MAX_IMAGE_PIXELS:
        raise ValueError(f"Output scaling terlalu besar. Maksimum {MAX_IMAGE_PIXELS} piksel.")
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
    tx=int_param(params, "tx", 50, -img.shape[1], img.shape[1]); ty=int_param(params, "ty", 50, -img.shape[0], img.shape[0])
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
    mode=choice_param(params, "mode", "horizontal", {"horizontal", "vertical", "both"})
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
    beta=int_param(params, "beta", 50, -255, 255); result=cv2.convertScaleAbs(img,alpha=1.0,beta=beta)
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
    alpha=float_param(params, "alpha", 1.5, 0.0, 3.0); result=cv2.convertScaleAbs(img,alpha=alpha,beta=0)
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
    tv=int_param(params, "threshold", 128, 0, 255); mode=choice_param(params, "mode", "binary", {"binary", "binary_inv", "otsu"})
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
    ksize=odd_int(int_param(params, "ksize", 3, 3, 31), 3, 31)
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
    ksize=odd_int(int_param(params, "ksize", 3, 3, 15), 3, 15)
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
    direction=choice_param(params, "direction", "both", {"x", "y", "both"})
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
    beta=int_param(params, "beta", 30, -100, 100); alpha=float_param(params, "alpha", 1.3, 0.5, 2.5)
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
    s_factor = float_param(params, "saturation", 50, -100, 100)

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
    shift = int_param(params, "hue", 30, -180, 180)

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
    amount = float_param(params, "amount", 1.0, 0.0, 5.0)

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
    sigma = float_param(params, "sigma", 2.0, 0.1, 10.0)
    ksize = odd_int(max(3, int(sigma * 3) | 1), 3, 31)

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
    opacity_val = float_param(params, "opacity", 50, 0, 100)  # 0-100
    bg_color = choice_param(params, "bg_color", "white", {"white", "black"})

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


def op_morphology(img, params):
    mode = choice_param(params, "mode", "dilation", {"dilation", "erosion", "opening", "closing", "boundary"})
    source = choice_param(params, "source", "binary", {"binary", "grayscale", "color"})
    ksize = odd_int(int_param(params, "ksize", 5, 3, 31), 3, 31)
    iterations = int_param(params, "iterations", 1, 1, 8)
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
    invert = bool_param(params, "invert", False)
    max_dim = int_param(params, "max_dim", 900, 200, 1200)
    max_iterations = int_param(params, "max_iterations", 80, 1, 120)
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
    method = choice_param(params, "method", "canny", {"canny", "sobel", "prewitt", "roberts", "laplacian"})
    blur_size = odd_int(int_param(params, "blur", 3, 1, 31), 1, 31)
    low = int_param(params, "low", 60, 0, 255)
    high = int_param(params, "high", 160, 0, 255)
    if low > high:
        low, high = high, low
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
    mode = choice_param(params, "mode", "otsu_blur", {"global_binary", "adaptive_gaussian", "kmeans", "otsu_blur"})
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if mode == "global_binary":
        threshold = int_param(params, "threshold", 127, 0, 255)
        _, segmented = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        formula = f"g=255 if f >= {threshold}, else 0"
    elif mode == "adaptive_gaussian":
        block_size = odd_int(int_param(params, "block_size", 21, 3, 99), 3, 99)
        c_value = int_param(params, "c", 5, -30, 30)
        segmented = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c_value)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        formula = f"local threshold = weighted mean({block_size}x{block_size}) - {c_value}"
    elif mode == "kmeans":
        clusters = int_param(params, "clusters", 4, 2, 8)
        data = img.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        centers = np.uint8(centers)
        result = centers[labels.flatten()].reshape(img.shape)
        formula = f"K-Means clustering with K={clusters}"
    else:
        blur_size = odd_int(int_param(params, "blur", 5, 3, 31), 3, 31)
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
    "morphology":       op_morphology,
    "zhang_suen":       op_zhang_suen,
    "edge_detection":   op_edge_detection,
    "segmentation":     op_segmentation,
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
    options = ensure_dict(options, "options")
    preset = choice_param(options, "preset", "document", {"document", "id", "receipt"})
    enhance = choice_param(options, "enhance", "balanced", {"soft", "balanced", "strong"})
    auto_crop = bool_param(options, "auto_crop", True)
    paper_size = choice_param(options, "paper_size", "auto", {"auto", "a4", "letter", "id"})
    output_max = int_param(options, "output_max", 1800, 900, 2600)

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
    stages[-1] = enrich_stage(stages[-1], work, blur)

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
    stages[-1] = enrich_stage(stages[-1], blur, edge_map)

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
    stages[-1] = enrich_stage(stages[-1], edge_map, contour_vis)

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
    stages[-1] = enrich_stage(stages[-1], original, warped_color)

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
    stages[-1] = enrich_stage(stages[-1], warped_gray, shadow_removed)

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
    stages[-1] = enrich_stage(stages[-1], shadow_removed, denoised_gray)

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
    stages[-1] = enrich_stage(stages[-1], denoised_gray, sharpened_gray)

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
    stages[-1] = enrich_stage(stages[-1], sharpened_gray, bw)

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
        data = request.get_json(silent=True) or {}
        img = decode_image(data.get("image"))
        options = ensure_dict(data.get("options") or {}, "options")
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
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return internal_error_response(e)

@app.route("/api/editor/apply", methods=["POST"])
@require_firebase_auth
def editor_apply():
    """
    Terapkan semua filter via OpenCV untuk export berkualitas tinggi.
    Lebih akurat dibanding CSS filter.
    """
    try:
        data   = request.get_json(silent=True) or {}
        img    = decode_image(data.get("image"))
        p      = ensure_dict(data.get("params", {}), "params")

        # Brightness + Contrast
        alpha = 1.0 + float_param(p, "contrast", 0, -100, 100) / 100.0
        beta  = float_param(p, "brightness", 0, -100, 100) * 2.55
        img   = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

        # Saturation
        sat = float_param(p, "saturation", 0, -100, 100)
        if sat != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:,:,1] = np.clip(hsv[:,:,1] * (1 + sat/100), 0, 255)
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Hue
        hue = int_param(p, "hue", 0, -180, 180)
        if hue != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int32)
            hsv[:,:,0] = (hsv[:,:,0] + hue // 2) % 180
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Blur
        blur_v = float_param(p, "blur", 0, 0, 100)
        if blur_v > 0:
            sigma = blur_v / 10.0
            ksize = max(3, int(sigma * 3) | 1)
            img = cv2.GaussianBlur(img, (ksize, ksize), sigma)

        # Sharpness (Unsharp Mask)
        sharp = float_param(p, "sharpness", 0, 0, 100)
        if sharp > 0:
            blur_img = cv2.GaussianBlur(img, (0, 0), 2)
            img = cv2.convertScaleAbs(
                img.astype(np.float32) + (sharp/100*2) * (img.astype(np.float32) - blur_img.astype(np.float32))
            )

        # Opacity
        opacity_v = float_param(p, "opacity", 100, 0, 100)
        if opacity_v < 100:
            a = opacity_v / 100.0
            white = np.full_like(img, 255)
            img = cv2.addWeighted(img, a, white, 1-a, 0)

        # Rotation
        angle = int_param(p, "rotation", 0, -360, 360)
        if angle != 0:
            h, w = img.shape[:2]
            M = cv2.getRotationMatrix2D((w//2, h//2), -angle, 1)
            img = cv2.warpAffine(img, M, (w, h))

        # Flip
        if bool_param(p, "flipH"): img = cv2.flip(img, 1)
        if bool_param(p, "flipV"): img = cv2.flip(img, 0)

        return jsonify({"result": encode_image(img)})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return internal_error_response(e)


# ══════════════════════════════════════════════════════
# MAIN API ROUTE
# ══════════════════════════════════════════════════════

@app.route("/api/process", methods=["POST"])
@require_firebase_auth
def process_image():
    try:
        data      = request.get_json(silent=True) or {}
        operation = str(data.get("operation", "grayscale"))
        params    = ensure_dict(data.get("params", {}), "params")
        image_b64 = data.get("image")
        if not image_b64:
            return jsonify({"error": "Tidak ada gambar"}), 400
        if operation not in OPERATIONS:
            return jsonify({"error": f"Operasi '{operation}' tidak dikenal. Tersedia: {list(OPERATIONS.keys())}"}), 400
        img = decode_image(image_b64)
        out = OPERATIONS[operation](img, params)
        return jsonify({"before": image_b64, "after": encode_image(out["result"]), "explanation": out["explanation"]})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return internal_error_response(e)

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







