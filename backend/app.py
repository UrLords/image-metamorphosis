import os, base64, functools, json, math, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from dotenv import load_dotenv
import numpy as np
import cv2
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
CORS_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv(
    "CORS_ORIGINS",
    f"{FRONTEND_URL},http://localhost:5173,http://127.0.0.1:5173,https://imagemeta.site",
).split(",") if origin.strip()]
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}}, supports_credentials=True)

FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
# -----------------------------------------------------------------------------
# Auth, storage, and persistence helpers
# -----------------------------------------------------------------------------

_firebase_auth = None
_cloudinary_ready = False
_persistence_executor = ThreadPoolExecutor(max_workers=int(os.getenv("PERSISTENCE_WORKERS", "2")))


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_firebase_auth():
    global _firebase_auth
    if _firebase_auth is not None:
        return _firebase_auth

    service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    project_id = os.getenv("FIREBASE_PROJECT_ID")

    if not service_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return None

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth
        from firebase_admin import credentials

        if not firebase_admin._apps:
            if service_json:
                info = json.loads(service_json, strict=False)
                if isinstance(info.get("private_key"), str):
                    info["private_key"] = info["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(info)
            else:
                cred = credentials.ApplicationDefault()
            options = {"projectId": project_id} if project_id else None
            firebase_admin.initialize_app(cred, options)

        _firebase_auth = firebase_auth
        return _firebase_auth
    except Exception as exc:
        print(f"Firebase Admin init failed: {exc}")
        return None


def verify_current_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, (jsonify({"error": "Authorization token is required"}), 401)

    firebase_auth = get_firebase_auth()
    if firebase_auth is None:
        return None, (jsonify({"error": "Firebase Admin is not configured on the backend"}), 503)

    try:
        decoded = firebase_auth.verify_id_token(header.split(" ", 1)[1].strip(), clock_skew_seconds=10)
        user = {
            "id": decoded.get("uid"),
            "firebase_uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name") or decoded.get("email"),
            "picture": decoded.get("picture"),
        }
        return user, None
    except Exception as exc:
        return None, (jsonify({"error": "Invalid Firebase token", "detail": str(exc)}), 401)


def require_auth(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user, error = verify_current_user()
        if error:
            return error
        g.current_user = user
        enqueue_persistence(sync_user_to_supabase, user, label="sync_user")
        return fn(*args, **kwargs)
    return wrapper


def enqueue_persistence(fn, *args, label="persistence", **kwargs):
    try:
        future = _persistence_executor.submit(fn, *args, **kwargs)
        future.add_done_callback(lambda f: print(f"{label} failed: {f.exception()}") if f.exception() else None)
        return True
    except Exception as exc:
        print(f"{label} enqueue failed: {exc}")
        return False


def supabase_request(table, payload, *, upsert=False, on_conflict="id"):
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        return None

    try:
        import requests
        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=merge-duplicates" if upsert else "return=minimal",
        }
        params = {"on_conflict": on_conflict} if upsert else None
        response = requests.post(
            f"{supabase_url}/rest/v1/{table}",
            params=params,
            headers=headers,
            json=payload,
            timeout=20,
        )
        if response.status_code >= 400:
            print(f"Supabase {table} write failed: {response.status_code} {response.text}")
        return response
    except Exception as exc:
        print(f"Supabase {table} write skipped: {exc}")
        return None


def sync_user_to_supabase(user):
    if not user or not user.get("id"):
        return

    supabase_request(
        "users",
        {
            "id": user["id"],
            "firebase_uid": user["firebase_uid"],
            "email": user.get("email"),
            "name": user.get("name"),
            "avatar_url": user.get("picture"),
            "updated_at": utc_now_iso(),
        },
        upsert=True,
        on_conflict="id",
    )


def configure_cloudinary():
    global _cloudinary_ready
    if _cloudinary_ready:
        return True

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    if not cloud_name or not api_key or not api_secret:
        return False

    try:
        import cloudinary
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
        _cloudinary_ready = True
        return True
    except Exception as exc:
        print(f"Cloudinary config failed: {exc}")
        return False


def upload_base64_to_cloudinary(data_url, user_id, folder, public_label):
    if not configure_cloudinary():
        return {"url": data_url, "public_id": None, "stored": False}

    try:
        from cloudinary.uploader import upload
        result = upload(
            data_url,
            folder=f"image-metamorphosis/{user_id}/{folder}",
            public_id=f"{public_label}-{uuid.uuid4().hex[:10]}",
            overwrite=False,
            resource_type="image",
        )
        return {"url": result.get("secure_url"), "public_id": result.get("public_id"), "stored": True}
    except Exception as exc:
        print(f"Cloudinary upload skipped: {exc}")
        return {"url": data_url, "public_id": None, "stored": False}


def save_image_metadata(user_id, operation, kind, upload_result):
    if not upload_result:
        return
    supabase_request(
        "images",
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "operation": operation,
            "kind": kind,
            "url": upload_result.get("url"),
            "public_id": upload_result.get("public_id"),
            "created_at": utc_now_iso(),
        },
    )


def save_processing_history(user_id, operation, input_upload, output_uploads, metadata=None):
    supabase_request(
        "processing_history",
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "operation": operation,
            "input_url": (input_upload or {}).get("url"),
            "input_public_id": (input_upload or {}).get("public_id"),
            "output_url": next((item.get("url") for item in output_uploads.values() if item), None),
            "outputs": output_uploads,
            "metadata": metadata or {},
            "created_at": utc_now_iso(),
        },
    )


def persist_processed_image(user, operation, image_b64, after_b64, params=None):
    input_upload = upload_base64_to_cloudinary(image_b64, user["id"], "originals", operation)
    output_upload = upload_base64_to_cloudinary(after_b64, user["id"], "processed", operation)
    save_image_metadata(user["id"], operation, "original", input_upload)
    save_image_metadata(user["id"], operation, "processed", output_upload)
    save_processing_history(user["id"], operation, input_upload, {"processed": output_upload}, {"params": params or {}})


def persist_scan_document(user, image_b64, scan_output):
    input_upload = upload_base64_to_cloudinary(image_b64, user["id"], "originals", "scan-original")
    output_uploads = {
        "bw": upload_base64_to_cloudinary(scan_output["bw"], user["id"], "processed", "scan-bw"),
        "grayscale": upload_base64_to_cloudinary(scan_output["grayscale"], user["id"], "processed", "scan-grayscale"),
        "color": upload_base64_to_cloudinary(scan_output["color"], user["id"], "processed", "scan-color"),
    }

    save_image_metadata(user["id"], "scan_document", "original", input_upload)
    for kind, upload_result in output_uploads.items():
        save_image_metadata(user["id"], "scan_document", kind, upload_result)
    save_processing_history(
        user["id"],
        "scan_document",
        input_upload,
        output_uploads,
        {"doc_detected": scan_output["doc_detected"], "output_resolution": scan_output["output_resolution"]},
    )

# ------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------

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

def get_histogram(img: np.ndarray) -> dict:
    try:
        img = img.astype(np.uint8) if img.dtype != np.uint8 else img
        h, w = img.shape[:2]
        max_dim = 900
        scale = min(1.0, max_dim / max(h, w))
        if scale < 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        def normalized_hist(channel):
            hist = cv2.calcHist([channel], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            return [float(v[0]) if math.isfinite(float(v[0])) else 0.0 for v in hist]

        if len(img.shape) == 2:
            luminance = normalized_hist(img)
            return {
                "red": [0.0] * 256,
                "green": [0.0] * 256,
                "blue": [0.0] * 256,
                "luminance": luminance,
            }

        b, g, r = cv2.split(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return {
            "red": normalized_hist(r),
            "green": normalized_hist(g),
            "blue": normalized_hist(b),
            "luminance": normalized_hist(gray),
        }
    except:
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
        "description": "Setiap piksel RGB -> satu nilai luminance. Bobot berbeda karena mata manusia lebih sensitif terhadap hijau.",
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "steps": [f"R={r_}, G={g}, B={b}", f"L = 0.299x{r_} + 0.587x{g} + 0.114x{b} = {lum} ~= {int(lum)}"],
        "image_info": {"width": w, "height": h, "mode": "BGR->Grayscale", "size_kb": round(w*h*3/1024,1)},
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
        "description": f"Dua gambar digabungkan dengan alpha={alpha} dan (1-alpha)={(1-alpha):.2f}.",
        "steps": [f"alpha={alpha}", f"Piksel img1[0,0]: {p1}", f"Piksel img2[0,0]: {p2}", f"Output ~= {[round(alpha*a+(1-alpha)*b) for a,b in zip(p1,p2)]}"],
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
        "description": "Background (Gaussian blur 51x51) dikurangi dari gambar asli.",
        "steps": ["B(x,y) = GaussianBlur(f, 51x51)", f"Piksel asli[10,10]: {p1}", f"Background[10,10]: {p2}", f"D = {[abs(int(a)-int(b)) for a,b in zip(p1,p2)]}"],
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
        "steps": ["Nilai piksel f1 x f2", "Dibagi 255 untuk mencegah overflow", "Piksel hitam di img2 -> area jadi hitam total"],
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
        "steps": ["Piksel 0 di img2 -> diganti 1 agar tidak error (ZeroDivision)", "f1 / f2 x 255", "Area gelap akibat bayangan bisa kembali normal"],
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
        "description": f"Rotasi {angle} deg terhadap pusat ({cx},{cy}).",
        "steps": [f"theta={angle} deg, costheta={round(math.cos(rad),4)}, sintheta={round(math.sin(rad),4)}", f"Pusat: ({cx},{cy})"],
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
        "steps": [f"Asli: {w}x{h}", f"Baru: {nw}x{nh}", "Interpolasi bilinear untuk mengisi piksel."],
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
        "steps": [f"M = [[1,0,{tx}],[0,1,{ty}]]", f"Piksel (50,30) -> ({50+tx},{30+ty})"],
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
        "description": f"beta={beta} ditambahkan ke setiap piksel.",
        "steps": [f"beta={beta}", f"Piksel[0,0]B: {p}", f"g={p}+{beta}={p+beta}", f"Clip->{po}"],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

def op_contrast(img, params):
    alpha=float(params.get("alpha",1.5)); result=cv2.convertScaleAbs(img,alpha=alpha,beta=0)
    p=int(img[0,0,0]); po=min(255,max(0,int(alpha*p)))
    return {"result": result, "explanation": {
        "title": "Contrast (Kontras)",
        "formula": r"g(x,y) = \text{clip}(\alpha \cdot f(x,y),\;0,\;255)",
        "description": f"alpha={alpha}. alpha>1 meningkatkan, alpha<1 mengurangi kontras.",
        "steps": [f"alpha={alpha}", f"Piksel[0,0]B: {p}", f"g={alpha}x{p}={round(alpha*p,2)}", f"Clip->{po}"],
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
        "title": f"Mean Filter ({ksize}x{ksize})",
        "formula": r"g(x,y) = \frac{1}{k^2}\sum_{m,n \in W} f(x+m, y+n)",
        "description": f"Rata-rata {ksize}x{ksize}={ksize*ksize} tetangga. Mengurangi noise acak.",
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
        "title": f"Median Filter ({ksize}x{ksize})",
        "formula": r"g(x,y) = \text{median}\{f(x+m, y+n) \;|\; m,n \in W\}",
        "description": f"Median dari {ksize}x{ksize} tetangga. Efektif untuk salt-and-pepper noise.",
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
        "steps": ["Kernel Sobel dikonvolusi dengan gambar grayscale", "Magnitude = sqrt(Gx^2+Gy^2)"],
    }}

def op_morphology(img, params):
    mode = params.get("mode", "dilation")
    source = params.get("source", "binary")
    ksize = int(params.get("ksize", 5))
    iterations = int(params.get("iterations", 1))
    ksize = max(3, ksize + 1 if ksize % 2 == 0 else ksize)
    iterations = max(1, min(iterations, 10))

    kernel = np.ones((ksize, ksize), np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if source == "color":
        work = img
        before_matrix = get_pixel_matrix(img, n=min(ksize, 5))
    elif source == "grayscale":
        work = gray
        before_matrix = get_pixel_matrix(gray, n=min(ksize, 5))
    else:
        _, work = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        before_matrix = get_pixel_matrix(work, n=min(ksize, 5))
        source = "binary"

    if mode == "erosion":
        processed = cv2.erode(work, kernel, iterations=iterations)
        title = "Erosion (Erosi)"
        formula = r"A \ominus B"
        description = "Erosi menipiskan objek dengan mengurangi piksel pada kontur sesuai structuring element."
        concept = "Objek putih mengecil; detail tipis dan noise kecil dapat hilang."
    elif mode == "opening":
        processed = cv2.morphologyEx(work, cv2.MORPH_OPEN, kernel, iterations=iterations)
        title = "Opening"
        formula = r"A \circ B = (A \ominus B) \oplus B"
        description = "Opening adalah erosi lalu dilasi. Cocok untuk menghapus tonjolan tipis dan noise kecil."
        concept = "Menghaluskan bentuk objek dan menghilangkan bagian sempit/penonjolan tipis."
    elif mode == "closing":
        processed = cv2.morphologyEx(work, cv2.MORPH_CLOSE, kernel, iterations=iterations)
        title = "Closing"
        formula = r"A \bullet B = (A \oplus B) \ominus B"
        description = "Closing adalah dilasi lalu erosi. Cocok untuk menutup lubang kecil dan gap pada kontur."
        concept = "Mengisi celah tipis, lubang kecil, dan retakan kecil pada objek."
    elif mode == "boundary":
        eroded = cv2.erode(work, kernel, iterations=iterations)
        processed = cv2.subtract(work, eroded)
        title = "Boundary Extraction"
        formula = r"\partial A = A - (A \ominus B)"
        description = "Ekstraksi batas mendapatkan tepi objek dengan mengurangi hasil erosi dari citra asal."
        concept = "Hanya kontur/batas objek yang dipertahankan."
    else:
        processed = cv2.dilate(work, kernel, iterations=iterations)
        mode = "dilation"
        title = "Dilation (Dilasi)"
        formula = r"A \oplus B"
        description = "Dilasi menumbuhkan atau menebalkan objek pada citra biner."
        concept = "Objek putih membesar; gap kecil pada garis atau teks dapat tersambung."

    result = processed if processed.ndim == 3 else cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
    after_matrix = get_pixel_matrix(processed, n=min(ksize, 5))

    return {"result": result, "explanation": {
        "title": title,
        "formula": formula,
        "description": description,
        "kernel": kernel.tolist(),
        "steps": [
            f"Source: {source}",
            f"Structuring element: kotak {ksize}x{ksize}",
            f"Iterations: {iterations}",
            concept,
        ],
        "pixel_before": before_matrix,
        "pixel_after": after_matrix,
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}

def op_enhance_pipeline(img, params):
    beta=int(params.get("beta",30)); alpha=float(params.get("alpha",1.3))
    s1=cv2.convertScaleAbs(img,alpha=1.0,beta=beta); s2=cv2.convertScaleAbs(s1,alpha=alpha,beta=0)
    blur=cv2.GaussianBlur(s2,(0,0),3); s3=cv2.addWeighted(s2,1.5,blur,-0.5,0)
    result=cv2.medianBlur(s3,3)
    return {"result": result, "explanation": {
        "title": "Enhancement Pipeline",
        "formula": r"g=\text{Median}(\text{Sharpen}(\alpha\cdot(f+\beta)))",
        "description": "Pipeline: Brightness->Contrast->Sharpening->Denoising.",
        "steps": [f"1. Brightness: g1=f+{beta}", f"2. Contrast: g2={alpha}xg1", "3. Unsharp Mask: g3=1.5xg2-0.5xBlur", "4. Median: g4=Median(g3,3)"],
        "pipeline": [{"name":"Original","beta":0,"alpha":1.0},{"name":"+Brightness","beta":beta,"alpha":1.0},{"name":"+Contrast","beta":beta,"alpha":alpha},{"name":"+Sharpen+Denoise","beta":beta,"alpha":alpha}],
        "pixel_before": get_pixel_matrix(img), "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img), "histogram_after": get_histogram(result),
    }}

# ------------------------------------------------------------------------
# NEW EDUCATIONAL OPERATIONS
# ------------------------------------------------------------------------

def op_saturation(img, params):
    """
    Saturasi: ubah kejenuhan warna via ruang HSV
    s > 0  -> warna lebih jenuh/vivid
    s < 0  -> warna memudar (menuju grayscale)
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
            "Ruang warna dikonversi BGR->HSV, channel S (kejenuhan) dimodifikasi, lalu dikembalikan ke BGR. "
            "s=+100 menggandakan saturasi, s=-100 -> gambar grayscale."
        ),
        "steps": [
            "1. Konversi BGR -> HSV (Hue 0-180 di OpenCV, Saturation 0-255, Value 0-255)",
            f"   scale = 1 + {s_factor}/100 = {round(scale,2)}",
            f"2. Piksel [0,0] HSV asli: H={p_h}, S={p_s}, V={p_v}",
            f"3. S' = clip({p_s} x {round(scale,2)}, 0, 255) = {p_s_new}",
            "4. Konversi HSV -> BGR untuk ditampilkan kembali",
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
            f"Hue digeser {shift} deg. Roda warna diputar: merah->kuning->hijau->biru->ungu->merah. "
            "OpenCV menggunakan rentang H: 0-180 (bukan 0-360)."
        ),
        "steps": [
            "1. BGR -> HSV",
            f"   Delta hue = {shift} deg. Karena OpenCV memakai skala 0-180, nilai internal bergeser {shift//2}",
            f"2. Piksel [0,0] Hue asli: {p_h} (={p_h*2} deg aktual)",
            f"3. H' = ({p_h} + {shift//2}) mod 180 = {p_h_new}",
            "4. HSV -> BGR",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_sharpness(img, params):
    """
    Sharpness via Unsharp Masking:
    g = clip(img + amount x (img - GaussianBlur(img)))
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
        "title": "Sharpness (Ketajaman) - Unsharp Masking",
        "formula": r"g(x,y) = \text{clip}(f(x,y) + a \cdot (f(x,y) - \text{Blur}(f(x,y))),\;0,\;255)",
        "description": (
            f"Unsharp Masking dengan amount={amount}. "
            "Blur dikurangi dari asli menghasilkan 'detail mask'. "
            "Detail mask ditambahkan kembali ke gambar asli."
        ),
        "steps": [
            "1. Buat blur: B = GaussianBlur(f, sigma=2)",
            f"   Amount a = {amount}",
            "2. Hitung detail mask: D = f - B",
            "3. Tambah ke asli: g = f + a x D",
            f"4. Piksel [10,10]: f={p_b}, B={p_blur}, D={p_b-p_blur}",
            f"   g = {p_b} + {amount}x{p_b-p_blur} = {p_sharp}",
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
        "title": f"Gaussian Blur (sigma={sigma})",
        "formula": r"G(x,y) = \frac{1}{2\pi\sigma^2} e^{-\frac{x^2+y^2}{2\sigma^2}}",
        "description": (
            f"Gaussian Blur dengan sigma={sigma}, kernel {ksize}x{ksize}. "
            "Piksel lebih dekat ke pusat mendapat bobot lebih besar (distribusi normal). "
            "Lebih halus dari Mean Filter karena tidak memotong frekuensi secara tiba-tiba."
        ),
        "kernel": kernel_show[:min(5, ksize)],
        "steps": [
            f"sigma = {sigma}, ksize = {ksize}x{ksize}",
            f"G(0,0) = 1 / (2 x pi x {sigma}^2) -> bobot terbesar di pusat",
            f"G(1,0) ~= exp(-1 / (2 x {sigma}^2)) x bobot pusat",
            "Total semua bobot = 1.0 (normalized)",
            "Setiap piksel = Sum(kernel x tetangga)",
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
            f"alpha = {opacity_val}/100 = {alpha}",
            f"Background B = {'putih (255,255,255)' if bg_color=='white' else 'hitam (0,0,0)'}",
            f"Piksel [0,0] asli: {p}",
            f"g = {alpha}x{p} + {1-alpha:.2f}x{bg_p}",
            f"g ~= {p_out}",
        ],
        "pixel_before": get_pixel_matrix(img),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}

def resize_for_analysis(img: np.ndarray, max_dim: int = 1200) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale >= 1.0:
        return img, 1.0
    resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def zhang_suen_thinning(binary: np.ndarray, max_iterations: int = 80) -> tuple[np.ndarray, int]:
    img01 = (binary > 0).astype(np.uint8)
    iterations = 0

    def transitions(neighbors):
        sequence = neighbors + [neighbors[0]]
        return sum(sequence[i] == 0 and sequence[i + 1] == 1 for i in range(8))

    while iterations < max_iterations:
        changed = False
        for step in (0, 1):
            to_delete = []
            rows, cols = img01.shape
            for y in range(1, rows - 1):
                for x in range(1, cols - 1):
                    if img01[y, x] != 1:
                        continue
                    p2 = img01[y - 1, x]
                    p3 = img01[y - 1, x + 1]
                    p4 = img01[y, x + 1]
                    p5 = img01[y + 1, x + 1]
                    p6 = img01[y + 1, x]
                    p7 = img01[y + 1, x - 1]
                    p8 = img01[y, x - 1]
                    p9 = img01[y - 1, x - 1]
                    neighbors = [p2, p3, p4, p5, p6, p7, p8, p9]
                    count = int(sum(neighbors))
                    if count < 2 or count > 6:
                        continue
                    if transitions(neighbors) != 1:
                        continue
                    if step == 0:
                        if p2 * p4 * p6 != 0 or p4 * p6 * p8 != 0:
                            continue
                    else:
                        if p2 * p4 * p8 != 0 or p2 * p6 * p8 != 0:
                            continue
                    to_delete.append((y, x))
            if to_delete:
                changed = True
                for y, x in to_delete:
                    img01[y, x] = 0
        iterations += 1
        if not changed:
            break

    return (img01 * 255).astype(np.uint8), iterations


def op_zhang_suen_thinning(img, params):
    max_dim = int(params.get("max_dim", 900))
    invert = bool(params.get("invert", False))
    work_img, scale = resize_for_analysis(img, max_dim=max_dim)
    gray = cv2.cvtColor(work_img, cv2.COLOR_BGR2GRAY)
    thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    threshold_value, binary = cv2.threshold(gray, 0, 255, thresh_type + cv2.THRESH_OTSU)
    skeleton, iterations = zhang_suen_thinning(binary, max_iterations=int(params.get("max_iterations", 80)))
    result = cv2.cvtColor(skeleton, cv2.COLOR_GRAY2BGR)

    return {"result": result, "explanation": {
        "title": "Thinning Zhang-Suen",
        "formula": r"S(A)=\text{iterasi penghapusan piksel batas sampai stabil}",
        "description": "Thinning mereduksi objek menjadi skeleton satu piksel tanpa menghilangkan struktur utama objek.",
        "steps": [
            f"Resize kerja: scale={round(scale, 3)} untuk menjaga proses tetap responsif",
            f"Otsu threshold T={round(float(threshold_value), 2)}, invert={invert}",
            "Setiap iterasi menjalankan dua sub-iterasi paralel Zhang-Suen",
            "Piksel batas dihapus hanya jika konektivitas objek tetap terjaga",
            f"Konvergen setelah {iterations} iterasi",
        ],
        "pixel_before": get_pixel_matrix(binary),
        "pixel_after": get_pixel_matrix(skeleton),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_edge_detection(img, params):
    method = params.get("method", "canny")
    blur = int(params.get("blur", 3))
    blur = blur + 1 if blur % 2 == 0 else blur
    blur = max(1, min(blur, 21))
    low = int(params.get("low", 60))
    high = int(params.get("high", 160))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    work = cv2.GaussianBlur(gray, (blur, blur), 0) if blur > 1 else gray

    if method == "prewitt":
        kx = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
        ky = np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], dtype=np.float32)
        gx = cv2.filter2D(work, cv2.CV_32F, kx)
        gy = cv2.filter2D(work, cv2.CV_32F, ky)
        edge = np.clip(cv2.magnitude(gx, gy), 0, 255).astype(np.uint8)
        formula = r"G=\sqrt{(P_x*f)^2+(P_y*f)^2}"
        kernel = kx.tolist()
        title = "Prewitt Edge Detection"
        concept = "Prewitt menghitung gradien dengan bobot sederhana; cocok untuk tepi dasar."
    elif method == "roberts":
        kx = np.array([[1, 0], [0, -1]], dtype=np.float32)
        ky = np.array([[0, 1], [-1, 0]], dtype=np.float32)
        gx = cv2.filter2D(work, cv2.CV_32F, kx)
        gy = cv2.filter2D(work, cv2.CV_32F, ky)
        edge = np.clip(cv2.magnitude(gx, gy), 0, 255).astype(np.uint8)
        formula = r"G=\sqrt{(R_x*f)^2+(R_y*f)^2}"
        kernel = kx.tolist()
        title = "Roberts Edge Detection"
        concept = "Roberts sensitif pada perubahan diagonal dan memakai kernel kecil 2x2."
    elif method == "laplacian":
        lap = cv2.Laplacian(work, cv2.CV_64F, ksize=3)
        edge = cv2.convertScaleAbs(lap)
        formula = r"\nabla^2 f = \frac{\partial^2 f}{\partial x^2}+\frac{\partial^2 f}{\partial y^2}"
        kernel = [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
        title = "Laplacian Edge Detection"
        concept = "Laplacian memakai turunan kedua; kuat untuk transisi intensitas tetapi lebih sensitif noise."
    elif method == "sobel":
        sx = cv2.Sobel(work, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(work, cv2.CV_64F, 0, 1, ksize=3)
        edge = np.clip(cv2.magnitude(sx, sy), 0, 255).astype(np.uint8)
        formula = r"G=\sqrt{G_x^2+G_y^2}"
        kernel = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
        title = "Sobel Edge Detection"
        concept = "Sobel menekankan gradien horizontal dan vertikal dengan smoothing kecil."
    else:
        edge = cv2.Canny(work, low, high)
        method = "canny"
        formula = r"\text{Canny}= \text{Gaussian} \rightarrow \nabla f \rightarrow \text{NMS} \rightarrow \text{Hysteresis}"
        kernel = None
        title = "Canny Edge Detection"
        concept = "Canny menggabungkan smoothing, gradien, non-maximum suppression, dan hysteresis threshold."

    result = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)
    return {"result": result, "explanation": {
        "title": title,
        "formula": formula,
        "description": "Edge detection menemukan batas antar region berdasarkan perubahan intensitas yang tajam, landai, atau mengandung noise.",
        "kernel": kernel,
        "steps": [
            f"Method: {method}",
            f"Gaussian smoothing kernel: {blur}x{blur}",
            "Tepi curam menghasilkan gradien tinggi dalam jarak pendek",
            "Tepi landai menghasilkan gradien lebih menyebar",
            "Noise dikurangi dengan smoothing sebelum deteksi tepi",
            f"Threshold Canny low/high: {low}/{high}" if method == "canny" else concept,
        ],
        "pixel_before": get_pixel_matrix(gray),
        "pixel_after": get_pixel_matrix(edge),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


def op_image_segmentation(img, params):
    mode = params.get("mode", "global_binary")
    threshold = int(params.get("threshold", 127))
    block_size = int(params.get("block_size", 21))
    c_value = int(params.get("c", 5))
    clusters = int(params.get("clusters", 4))
    blur = int(params.get("blur", 5))

    block_size = max(3, block_size + 1 if block_size % 2 == 0 else block_size)
    blur = max(1, blur + 1 if blur % 2 == 0 else blur)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if mode.startswith("global_"):
        threshold_map = {
            "global_binary": cv2.THRESH_BINARY,
            "global_binary_inv": cv2.THRESH_BINARY_INV,
            "global_trunc": cv2.THRESH_TRUNC,
            "global_tozero": cv2.THRESH_TOZERO,
            "global_tozero_inv": cv2.THRESH_TOZERO_INV,
        }
        cv_mode = threshold_map.get(mode, cv2.THRESH_BINARY)
        _, segmented = cv2.threshold(gray, threshold, 255, cv_mode)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        title = "Global Thresholding"
        formula = r"g(x,y)=T(f(x,y),127)"
        description = "Segmentasi berbasis ambang tunggal. Semua piksel dibandingkan dengan nilai threshold yang sama."
        steps = [
            f"Mode: {mode.replace('global_', '').upper()}",
            f"Threshold T={threshold}",
            "BINARY memisahkan objek menjadi hitam/putih",
            "TRUNC memotong nilai di atas T",
            "TOZERO mempertahankan nilai tertentu dan mengubah sisanya menjadi 0",
        ]
    elif mode in ("adaptive_mean", "adaptive_gaussian"):
        adaptive_method = cv2.ADAPTIVE_THRESH_MEAN_C if mode == "adaptive_mean" else cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        segmented = cv2.adaptiveThreshold(gray, 255, adaptive_method, cv2.THRESH_BINARY, block_size, c_value)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        title = "Adaptive Thresholding"
        formula = r"g(x,y)=255 \text{ jika } f(x,y) > \mu_W-C"
        description = "Adaptive thresholding memakai ambang lokal dari area tetangga sehingga cocok untuk pencahayaan tidak merata."
        steps = [
            f"Method: {'MEAN' if mode == 'adaptive_mean' else 'GAUSSIAN'}",
            f"Block size: {block_size}x{block_size}",
            f"C={c_value}",
            "Ambang dihitung per area lokal, bukan satu threshold global",
        ]
    elif mode in ("otsu", "otsu_blur"):
        work = cv2.GaussianBlur(gray, (blur, blur), 0) if mode == "otsu_blur" else gray
        otsu_t, segmented = cv2.threshold(work, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
        title = "Otsu's Binarization"
        formula = r"T^*=\arg\max_T \sigma_B^2(T)"
        description = "Otsu mencari threshold optimal otomatis dengan memaksimalkan variance antar kelas foreground dan background."
        steps = [
            f"Gaussian pre-filter: {'yes' if mode == 'otsu_blur' else 'no'}",
            f"Otsu threshold T*={round(float(otsu_t), 2)}",
            "Gaussian filtering membantu ketika citra mengandung noise",
            "Output membagi citra menjadi dua kelas utama",
        ]
    else:
        small, scale = resize_for_analysis(img, max_dim=int(params.get("max_dim", 900)))
        clusters = max(2, min(clusters, 8))
        pixels = small.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(pixels, clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        centers = np.uint8(centers)
        segmented_small = centers[labels.flatten()].reshape(small.shape)
        result = cv2.resize(segmented_small, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST) if scale < 1 else segmented_small
        title = "K-Means Color Segmentation"
        formula = r"\arg\min \sum_i \|x_i-\mu_{c_i}\|^2"
        description = "K-Means mengelompokkan piksel warna RGB berdasarkan kemiripan warna, lalu mengganti piksel dengan warna pusat clusternya."
        steps = [
            f"Jumlah cluster K={clusters}",
            f"Resize kerja scale={round(scale, 3)} agar clustering tetap cepat",
            "Setiap piksel RGB dipandang sebagai titik 3D: (R,G,B)",
            "K-Means mencari pusat warna yang mewakili region homogen",
            f"Center warna BGR: {centers.tolist()}",
        ]

    return {"result": result, "explanation": {
        "title": title,
        "formula": formula,
        "description": description,
        "steps": steps,
        "pixel_before": get_pixel_matrix(gray),
        "pixel_after": get_pixel_matrix(result),
        "histogram_before": get_histogram(img),
        "histogram_after": get_histogram(result),
    }}


# ------------------------------------------------------------------------
# OPERATIONS ROUTER
# ------------------------------------------------------------------------

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
    "morphology":       op_morphology,
    "zhang_suen":       op_zhang_suen_thinning,
    "edge_detection":   op_edge_detection,
    "segmentation":     op_image_segmentation,
    "enhance_pipeline": op_enhance_pipeline,
}

# ------------------------------------------------------------------------
# DOCUMENT SCANNER / RESTORATION PIPELINE (CamScanner-style)
# 8 tahap: Grayscale+Blur -> Canny Edge -> Contour+Quad Detection
#        -> Perspective Transform (deskew+crop) -> Shadow Removal
#        -> Noise Reduction -> Sharpening -> Adaptive Threshold + Mode Output
# ------------------------------------------------------------------------

def order_points(pts: np.ndarray) -> np.ndarray:
    """Urutkan 4 titik sudut menjadi [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]          # top-left  -> jumlah x+y terkecil
    rect[2] = pts[np.argmax(s)]          # bottom-right -> jumlah x+y terbesar
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]       # top-right -> selisih x-y terkecil
    rect[3] = pts[np.argmax(diff)]       # bottom-left -> selisih x-y terbesar
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
    median = float(np.median(blur))
    low = int(max(30, 0.66 * median))
    high = int(min(220, 1.33 * median + 40))
    edges = cv2.Canny(blur, low, high)
    edges_dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
    edges_dilated = cv2.morphologyEx(edges_dilated, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

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


def remove_tiny_dark_components(binary_white_bg: np.ndarray, min_area: int = 7) -> np.ndarray:
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

    # TAHAP 1: Grayscale + Gaussian Blur
    quad, contour_vis, edges_dilated, blur = find_document_quad(work)
    stages.append({
        "id": "preprocess", "order": 1,
        "title": "Grayscale + Gaussian Blur",
        "objective": "Menyederhanakan citra ke satu channel dan meredam noise sebelum deteksi tepi.",
        "formula": r"L=0.299R+0.587G+0.114B,\quad B(x,y)=G_{\sigma}(x,y)*L(x,y)",
        "math_concept": (
            "Citra dikonversi ke grayscale agar deteksi tepi tidak terganggu variasi warna, "
            "lalu di-blur dengan Gaussian 5x5 agar tekstur kertas/noise sensor tidak terdeteksi "
            "sebagai tepi palsu pada tahap Canny berikutnya."
        ),
        "description": "Kernel Gaussian 5x5, sigma otomatis dari OpenCV.",
        "image": encode_stage_preview(blur),
    })

    # TAHAP 2: Canny Edge Detection + Dilasi
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
        "description": "Threshold Canny: low=50, high=150. Dilasi kernel 5x5, 2 iterasi.",
        "image": encode_stage_preview(edges_dilated),
    })

    # TAHAP 3: Contour Detection + Deteksi Quad Dokumen
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
        "description": f"Dokumen {'terdeteksi' if quad is not None else 'TIDAK terdeteksi - memakai frame penuh'}.",
        "image": encode_stage_preview(contour_vis),
    })

    # TAHAP 4: Perspective Transform (Deskew + Auto-Crop)
    if quad is not None:
        pts_full = quad / scale  # map titik dari resolusi kerja -> resolusi asli
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
            "Homography H (matriks 3x3) dihitung dari 4 titik sudut dokumen menuju 4 titik persegi "
            "panjang tujuan. Transformasi ini memetakan ulang setiap piksel sehingga dokumen yang "
            "difoto miring/dari sudut tertentu menjadi tampak seperti hasil pindai datar (flatbed scan)."
        ),
        "description": f"Output: {mw}x{mh}px (sebelum cap resolusi proses).",
        "image": encode_stage_preview(warped_color),
    })

    warped_gray = cv2.cvtColor(warped_color, cv2.COLOR_BGR2GRAY)

    # TAHAP 5: Shadow/Stain Removal Koreksi Iluminasi
    bg_kernel = max(31, (min(warped_gray.shape[:2]) // 18) | 1)
    bg_estimate = cv2.medianBlur(cv2.dilate(warped_gray, np.ones((9, 9), np.uint8)), bg_kernel)
    bg_estimate[bg_estimate == 0] = 1
    shadow_removed = cv2.divide(warped_gray, bg_estimate, scale=255)
    shadow_removed = cv2.normalize(shadow_removed, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    lab = cv2.cvtColor(warped_color, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch_lab = cv2.split(lab)
    l_bg = cv2.medianBlur(cv2.dilate(l_ch, np.ones((9, 9), np.uint8)), bg_kernel)
    l_bg[l_bg == 0] = 1
    l_corrected = cv2.divide(l_ch, l_bg, scale=255)
    l_corrected = cv2.normalize(l_corrected, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    color_shadow_fixed = cv2.cvtColor(cv2.merge([l_corrected, a_ch, b_ch_lab]), cv2.COLOR_LAB2BGR)

    stages.append({
        "id": "shadow", "order": 5,
        "title": "Shadow Removal (Koreksi Iluminasi)",
        "objective": "Menghilangkan bayangan tangan/lipatan dan pencahayaan tidak merata pada permukaan dokumen.",
        "formula": r"B_{est}=\text{median}\big(\text{dilate}(I)\big),\quad I'=\frac{I}{B_{est}}\times255",
        "math_concept": (
            "Dilasi dan median blur membentuk estimasi background atau pola pencahayaan kertas. "
            "Citra asli dibagi dengan background estimate sehingga bayangan dan bercak halus diratakan, "
            "sementara teks/garis yang kontras tetap dipertahankan."
        ),
        "description": f"Dilasi 9x9, Median Blur kernel {bg_kernel} untuk estimasi background.",
        "image": encode_stage_preview(shadow_removed),
    })

    # TAHAP 6: Noise Reduction
    denoised_gray = cv2.fastNlMeansDenoising(shadow_removed, h=10, templateWindowSize=7, searchWindowSize=21)
    denoised_color = cv2.bilateralFilter(color_shadow_fixed, d=7, sigmaColor=50, sigmaSpace=50)
    stages.append({
        "id": "denoise", "order": 6,
        "title": "Noise Reduction",
        "objective": "Membersihkan bintik noise sensor kamera tanpa mengaburkan tepi teks.",
        "formula": r"NL[I]_p=\frac{1}{Z_p}\sum_{q\in S}w(p,q)\,I_q,\quad w(p,q)=e^{-\|N(p)-N(q)\|^2/h^2}",
        "math_concept": (
            "Non-Local Means Denoising (untuk jalur grayscale/B&W) membandingkan patch piksel di "
            "seluruh citra, bukan hanya tetangga lokal - patch yang mirip diberi bobot tinggi meski "
            "berjauhan, menghasilkan reduksi noise yang sangat bersih untuk teks. Jalur warna memakai "
            "Bilateral Filter (lebih cepat) agar gradasi warna tetap natural."
        ),
        "description": "Grayscale: fastNlMeansDenoising h=10. Warna: Bilateral d=7.",
        "image": encode_stage_preview(denoised_gray),
    })

    # TAHAP 7: Sharpening (Unsharp Masking)
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
            "detail ini ditambahkan kembali dengan bobot lebih - menonjolkan tepi tajam tanpa mengubah "
            "area datar/seragam."
        ),
        "description": "Gaussian sigma=2 untuk basis blur, amount 1.5 (gray) / 1.3 (warna).",
        "image": encode_stage_preview(sharpened_gray),
    })

    # TAHAP 8: Adaptive Thresholding + Output Modes
    bw = cv2.adaptiveThreshold(
        sharpened_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10
    )
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1)
    bw = remove_tiny_dark_components(bw, min_area=7)
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
            "menghitung ambang batas lokal mu (rata-rata Gaussian tetangga blockSize=25) per-piksel "
            "dikurangi konstanta C=10 - sehingga tetap akurat meski pencahayaan sedikit tidak merata "
            "antar area kertas. Mode Grayscale & Warna memakai CLAHE untuk kontras tanpa binerisasi."
        ),
        "description": "Adaptive Gaussian blockSize=25, C=10, lalu pembersihan speck kecil. CLAHE clipLimit=2.0, tile 8x8.",
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
        "output_resolution": f"{sharpened_gray.shape[1]}x{sharpened_gray.shape[0]}",
        "histogram_before": hist_before,
        "histogram_after": hist_after,
    }


# ------------------------------------------------------------------------
# ADVANCED EDITOR API ROUTES
# ------------------------------------------------------------------------


@app.route("/api/auth/firebase", methods=["POST"])
@require_auth
def auth_firebase():
    return jsonify({"ok": True, "user": g.current_user})

@app.route("/api/editor/scan-document", methods=["POST"])
@require_auth
def editor_scan_document():
    """
    Restorasi dan pemindaian dokumen bergaya CamScanner.
    Mengembalikan 3 output: grayscale, hitam-putih, dan warna enhanced.
    """
    try:
        data = request.get_json() or {}
        image_b64 = data.get("image")
        if not image_b64:
            return jsonify({"error": "Tidak ada gambar"}), 400

        img = decode_image(image_b64)
        out = run_document_scan_pipeline(img)

        user = g.current_user
        persist = data.get("persist", True)
        storage_status = "disabled"
        if persist:
            queued = enqueue_persistence(
                persist_scan_document,
                user.copy(),
                image_b64,
                out.copy(),
                label="persist_scan_document",
            )
            storage_status = "queued" if queued else "failed_to_queue"

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
            "storage": storage_status,
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/editor/apply", methods=["POST"])
@require_auth
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


# ------------------------------------------------------------------------
# MAIN API ROUTE
# ------------------------------------------------------------------------

@app.route("/api/process", methods=["POST"])
@require_auth
def process_image():
    try:
        data = request.get_json() or {}
        operation = data.get("operation", "grayscale")
        params = data.get("params", {})
        image_b64 = data.get("image")

        if not image_b64:
            return jsonify({"error": "Tidak ada gambar"}), 400
        if operation not in OPERATIONS:
            return jsonify({"error": f"Operasi '{operation}' tidak dikenal. Tersedia: {list(OPERATIONS.keys())}"}), 400

        img = decode_image(image_b64)
        out = OPERATIONS[operation](img, params)
        after_b64 = encode_image(out["result"])

        persist = bool(data.get("persist", False))
        storage_status = "disabled"
        if persist:
            queued = enqueue_persistence(
                persist_processed_image,
                g.current_user.copy(),
                operation,
                image_b64,
                after_b64,
                params.copy() if isinstance(params, dict) else params,
                label=f"persist_{operation}",
            )
            storage_status = "queued" if queued else "failed_to_queue"

        return jsonify({
            "before": image_b64,
            "after": after_b64,
            "explanation": out["explanation"],
            "storage": storage_status,
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
@app.route("/api/operations", methods=["GET"])
def list_ops():
    return jsonify({"operations": list(OPERATIONS.keys())})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.0.0", "operations": len(OPERATIONS)})

# Serve React build
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    file_path = os.path.join(FRONTEND_BUILD, path)
    if path and os.path.exists(file_path):
        return send_from_directory(FRONTEND_BUILD, path)
    return send_from_directory(FRONTEND_BUILD, "index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
