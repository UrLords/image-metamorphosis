import { useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import axios from "axios";
import {
  AlertCircle,
  Check,
  Crop,
  Download,
  FlipHorizontal2,
  FlipVertical2,
  ImageOff,
  Layers,
  Loader2,
  RefreshCw,
  RotateCcw,
  RotateCw,
  ScanLine,
  Scissors,
  Upload,
  X,
} from "lucide-react";
import PipelineModal, { type PipelineStage } from "../components/PipelineModal";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

interface PipelineResponse {
  result: string;
  method?: string;
  stages?: PipelineStage[];
  histogram_before?: number[];
  histogram_after?: number[];
  coverage_pct?: number;
}

type ScanMode = "color" | "grayscale" | "bw";

interface DocScanResponse {
  grayscale: string;
  bw: string;
  color: string;
  method?: string;
  stages?: PipelineStage[];
  doc_detected?: boolean;
  output_resolution?: string;
  histogram_before?: number[];
  histogram_after?: number[];
}

interface EditorState {
  brightness: number;
  contrast: number;
  saturation: number;
  blur: number;
  sharpness: number;
  hue: number;
  opacity: number;
}

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

const DEFAULT_STATE: EditorState = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  blur: 0,
  sharpness: 0,
  hue: 0,
  opacity: 100,
};

function buildFilter(state: EditorState) {
  return [
    `brightness(${1 + state.brightness / 100})`,
    `contrast(${1 + state.contrast / 100})`,
    `saturate(${Math.max(0, 1 + state.saturation / 100)})`,
    `hue-rotate(${state.hue}deg)`,
    state.blur > 0 ? `blur(${(state.blur / 10).toFixed(1)}px)` : "",
    state.sharpness > 0 ? `contrast(${1 + state.sharpness * 0.004})` : "",
  ]
    .filter(Boolean)
    .join(" ");
}

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (value: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <label className="block space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted">{label}</span>
        <span className="text-xs font-mono font-semibold text-accent">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-1 w-full cursor-pointer appearance-none rounded-full"
        style={{
          background: `linear-gradient(to right, #C9A86C ${pct}%, #2A3340 ${pct}%)`,
          accentColor: "#C9A86C",
        }}
      />
    </label>
  );
}

function ToolButton({
  icon: Icon,
  label,
  active = false,
  disabled = false,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={`flex w-full flex-col items-center justify-center gap-1 rounded-lg px-1 py-2 text-[10px] transition-all ${
        active
          ? "bg-accent text-[#0C1014]"
          : "text-muted hover:bg-white/10 hover:text-white"
      } ${disabled ? "cursor-not-allowed opacity-35" : ""}`}
    >
      <Icon size={17} />
      <span className="leading-none">{label}</span>
    </button>
  );
}

export default function AdvancedEditor() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [state, setState] = useState<EditorState>(DEFAULT_STATE);
  const [rotation, setRotation] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [activeTool, setActiveTool] = useState<"none" | "crop" | "cutout">(
    "none",
  );
  const [rect, setRect] = useState<Rect | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingText, setProcessingText] = useState("");
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });
  const [toast, setToast] = useState<{
    message: string;
    type: "ok" | "err";
  } | null>(null);

  // ── Classical CV pipeline breakdown (remove-bg / cutout) ──────────
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([]);
  const [pipelineMethod, setPipelineMethod] = useState<string | undefined>();
  const [pipelineCoverage, setPipelineCoverage] = useState<
    number | undefined
  >();
  const [pipelineHistBefore, setPipelineHistBefore] = useState<
    number[] | undefined
  >();
  const [pipelineHistAfter, setPipelineHistAfter] = useState<
    number[] | undefined
  >();
  const [showPipelineModal, setShowPipelineModal] = useState(false);

  // ── Document Scanner (CamScanner-style) ────────────────────────────
  const [scanResults, setScanResults] = useState<{
    color: string;
    grayscale: string;
    bw: string;
  } | null>(null);
  const [scanMode, setScanMode] = useState<ScanMode>("bw");
  const [docDetected, setDocDetected] = useState<boolean | undefined>();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const imageBoxRef = useRef<HTMLDivElement>(null);

  const cssFilter = useMemo(() => buildFilter(state), [state]);
  const cssTransform = useMemo(
    () =>
      [
        rotation ? `rotate(${rotation}deg)` : "",
        flipH ? "scaleX(-1)" : "",
        flipV ? "scaleY(-1)" : "",
      ]
        .filter(Boolean)
        .join(" ") || "none",
    [flipH, flipV, rotation],
  );

  const isModified =
    JSON.stringify(state) !== JSON.stringify(DEFAULT_STATE) ||
    rotation !== 0 ||
    flipH ||
    flipV ||
    imageUrl !== originalUrl;

  const showToast = (message: string, type: "ok" | "err" = "ok") => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 2600);
  };

  const patchState = (patch: Partial<EditorState>) =>
    setState((current) => ({ ...current, ...patch }));

  const handleFile = (file: File) => {
    if (!file.type.startsWith("image/")) {
      showToast("File harus berupa gambar.", "err");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result);
      setImageUrl(result);
      setOriginalUrl(result);
      setState(DEFAULT_STATE);
      setRotation(0);
      setFlipH(false);
      setFlipV(false);
      setRect(null);
      setActiveTool("none");
      setScanResults(null);
      setDocDetected(undefined);
      setPipelineStages([]);
    };
    reader.readAsDataURL(file);
  };

  const resetAll = () => {
    if (!originalUrl) return;
    setImageUrl(originalUrl);
    setState(DEFAULT_STATE);
    setRotation(0);
    setFlipH(false);
    setFlipV(false);
    setRect(null);
    setActiveTool("none");
    setScanResults(null);
    setDocDetected(undefined);
    showToast("Editor di-reset.");
  };

  const getPointer = (event: React.MouseEvent) => {
    const box = imageBoxRef.current;
    if (!box) return { x: 0, y: 0 };
    const bounds = box.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(event.clientX - bounds.left, bounds.width)),
      y: Math.max(0, Math.min(event.clientY - bounds.top, bounds.height)),
    };
  };

  const startSelection = (event: React.MouseEvent) => {
    if (activeTool === "none") return;
    event.preventDefault();
    const point = getPointer(event);
    setDragStart(point);
    setRect({ x: point.x, y: point.y, w: 0, h: 0 });
  };

  const updateSelection = (event: React.MouseEvent) => {
    if (!dragStart || activeTool === "none") return;
    const point = getPointer(event);
    setRect({
      x: Math.min(point.x, dragStart.x),
      y: Math.min(point.y, dragStart.y),
      w: Math.abs(point.x - dragStart.x),
      h: Math.abs(point.y - dragStart.y),
    });
  };

  const finishSelection = () => setDragStart(null);

  const applyCrop = () => {
    if (!rect || !imgRef.current || rect.w < 8 || rect.h < 8) {
      showToast("Area crop terlalu kecil.", "err");
      return;
    }

    const img = imgRef.current;
    const scaleX = img.naturalWidth / img.offsetWidth;
    const scaleY = img.naturalHeight / img.offsetHeight;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = Math.round(rect.w * scaleX);
    canvas.height = Math.round(rect.h * scaleY);
    ctx.drawImage(
      img,
      Math.round(rect.x * scaleX),
      Math.round(rect.y * scaleY),
      canvas.width,
      canvas.height,
      0,
      0,
      canvas.width,
      canvas.height,
    );
    const dataUrl = canvas.toDataURL("image/png");
    setImageUrl(dataUrl);
    setRect(null);
    setActiveTool("none");
    showToast("Crop berhasil.");
  };

  const callEditorEndpoint = async (
    path: "/editor/cutout" | "/editor/apply",
    payload: Record<string, unknown>,
    message: string,
  ) => {
    setIsProcessing(true);
    setProcessingText(message);
    try {
      const response = await axios.post<{ result: string }>(
        `${API_BASE_URL}${path}`,
        payload,
      );
      return response.data.result;
    } finally {
      setIsProcessing(false);
      setProcessingText("");
    }
  };

  const scanDocument = async () => {
    if (!imageUrl) return;
    setIsProcessing(true);
    setProcessingText(
      "Mendeteksi dokumen & menjalankan pipeline restorasi (8 tahap)...",
    );
    try {
      const response = await axios.post<DocScanResponse>(
        `${API_BASE_URL}/editor/scan-document`,
        { image: imageUrl },
      );
      const results = {
        color: response.data.color,
        grayscale: response.data.grayscale,
        bw: response.data.bw,
      };
      setScanResults(results);
      setDocDetected(response.data.doc_detected);
      setScanMode("bw");
      setImageUrl(results.bw);
      if (response.data.stages?.length) {
        setPipelineStages(response.data.stages);
        setPipelineMethod(response.data.method);
        setPipelineCoverage(undefined);
        setPipelineHistBefore(response.data.histogram_before);
        setPipelineHistAfter(response.data.histogram_after);
      }
      showToast(
        response.data.doc_detected
          ? "Dokumen terdeteksi & diluruskan — lihat breakdown pipeline."
          : "Tepi dokumen tidak terdeteksi, memakai frame penuh.",
      );
    } catch {
      showToast("Gagal scan dokumen. Cek backend API.", "err");
    } finally {
      setIsProcessing(false);
      setProcessingText("");
    }
  };

  const switchScanMode = (mode: ScanMode) => {
    if (!scanResults) return;
    setScanMode(mode);
    setImageUrl(scanResults[mode]);
  };

  const applyCutout = async () => {
    if (!imageUrl || !rect || !imgRef.current || rect.w < 8 || rect.h < 8) {
      showToast("Pilih area cutout terlebih dahulu.", "err");
      return;
    }

    const img = imgRef.current;
    const scaleX = img.naturalWidth / img.offsetWidth;
    const scaleY = img.naturalHeight / img.offsetHeight;

    setIsProcessing(true);
    setProcessingText("Menjalankan pipeline segmentasi (9 tahap)...");
    try {
      const response = await axios.post<PipelineResponse>(
        `${API_BASE_URL}/editor/cutout`,
        {
          image: imageUrl,
          rect: {
            x: Math.round(rect.x * scaleX),
            y: Math.round(rect.y * scaleY),
            w: Math.round(rect.w * scaleX),
            h: Math.round(rect.h * scaleY),
          },
        },
      );
      setImageUrl(response.data.result);
      if (response.data.stages?.length) {
        setPipelineStages(response.data.stages);
        setPipelineMethod(response.data.method);
        setPipelineCoverage(response.data.coverage_pct);
        setPipelineHistBefore(response.data.histogram_before);
        setPipelineHistAfter(response.data.histogram_after);
      }
      setRect(null);
      setActiveTool("none");
      showToast("Cutout berhasil — lihat breakdown pipeline.");
    } catch {
      showToast("Gagal cutout. Cek backend API.", "err");
    } finally {
      setIsProcessing(false);
      setProcessingText("");
    }
  };

  const downloadWithCanvasFallback = (format: "png" | "jpg") => {
    const img = imgRef.current;
    if (!img) return;

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rad = (rotation * Math.PI) / 180;
    const sin = Math.abs(Math.sin(rad));
    const cos = Math.abs(Math.cos(rad));
    canvas.width = Math.round(img.naturalWidth * cos + img.naturalHeight * sin);
    canvas.height = Math.round(
      img.naturalWidth * sin + img.naturalHeight * cos,
    );

    ctx.filter = cssFilter;
    ctx.globalAlpha = state.opacity / 100;
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(rad);
    ctx.scale(flipH ? -1 : 1, flipV ? -1 : 1);
    ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2);

    const link = document.createElement("a");
    link.download = `image-metamorphosis.${format}`;
    link.href = canvas.toDataURL(
      format === "jpg" ? "image/jpeg" : "image/png",
      0.95,
    );
    link.click();
  };

  const download = async (format: "png" | "jpg") => {
    if (!imageUrl) return;
    try {
      const result = await callEditorEndpoint(
        "/editor/apply",
        { image: imageUrl, params: { ...state, rotation, flipH, flipV } },
        "Mengekspor gambar...",
      );
      const link = document.createElement("a");
      link.download = `image-metamorphosis.${format}`;
      link.href = result;
      link.click();
      showToast(`Download ${format.toUpperCase()} berhasil.`);
    } catch {
      downloadWithCanvasFallback(format);
      showToast(`Download ${format.toUpperCase()} memakai fallback browser.`);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mx-auto flex max-w-7xl flex-col gap-4"
    >
      <div className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2
            className="text-2xl font-bold text-white"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Advanced Editor
          </h2>
          <p className="mt-1 text-sm text-muted">
            Preview real-time, crop, cutout, remove background, dan export.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-white transition hover:border-accent/50"
          >
            <Upload size={15} />
            Upload
          </button>
          <button
            type="button"
            onClick={resetAll}
            disabled={!imageUrl || !isModified}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-muted transition hover:text-white disabled:cursor-not-allowed disabled:opacity-35"
          >
            <RefreshCw size={15} />
            Reset
          </button>
          <button
            type="button"
            onClick={() => download("png")}
            disabled={!imageUrl || isProcessing}
            className="flex items-center gap-2 rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-sm font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-35"
          >
            <Download size={15} />
            PNG
          </button>
          <button
            type="button"
            onClick={() => download("jpg")}
            disabled={!imageUrl || isProcessing}
            className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-[#0C1014] transition hover:bg-accent/90 disabled:opacity-35"
          >
            <Download size={15} />
            JPG
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[72px_minmax(0,1fr)_300px]">
        <div className="flex gap-2 overflow-x-auto rounded-xl border border-border bg-card p-2 xl:flex-col xl:overflow-visible">
          <ToolButton
            icon={RotateCw}
            label="90"
            disabled={!imageUrl}
            onClick={() => setRotation((value) => (value + 90) % 360)}
          />
          <ToolButton
            icon={RotateCcw}
            label="-90"
            disabled={!imageUrl}
            onClick={() => setRotation((value) => (value + 270) % 360)}
          />
          <ToolButton
            icon={FlipHorizontal2}
            label="Flip H"
            active={flipH}
            disabled={!imageUrl}
            onClick={() => setFlipH((value) => !value)}
          />
          <ToolButton
            icon={FlipVertical2}
            label="Flip V"
            active={flipV}
            disabled={!imageUrl}
            onClick={() => setFlipV((value) => !value)}
          />
          <ToolButton
            icon={Crop}
            label="Crop"
            active={activeTool === "crop"}
            disabled={!imageUrl}
            onClick={() => {
              setRect(null);
              setActiveTool((value) => (value === "crop" ? "none" : "crop"));
            }}
          />
          <ToolButton
            icon={Scissors}
            label="Cutout"
            active={activeTool === "cutout"}
            disabled={!imageUrl}
            onClick={() => {
              setRect(null);
              setActiveTool((value) =>
                value === "cutout" ? "none" : "cutout",
              );
            }}
          />
          <ToolButton
            icon={ScanLine}
            label="Scan Docs"
            disabled={!imageUrl || isProcessing}
            onClick={scanDocument}
          />
        </div>

        {scanResults && (
          <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-2">
            <span className="px-1 text-[11px] text-muted">Mode Output:</span>
            {[
              { mode: "bw" as ScanMode, label: "Hitam-Putih" },
              { mode: "grayscale" as ScanMode, label: "Grayscale" },
              { mode: "color" as ScanMode, label: "Warna" },
            ].map(({ mode, label }) => (
              <button
                key={mode}
                type="button"
                onClick={() => switchScanMode(mode)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  scanMode === mode
                    ? "bg-accent text-[#0C1014]"
                    : "border border-border bg-bg text-muted hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
            {docDetected === false && (
              <span className="ml-auto flex items-center gap-1 text-[11px] text-yellow-400">
                <AlertCircle size={11} /> Tepi tidak terdeteksi — frame penuh
                dipakai
              </span>
            )}
          </div>
        )}

        <div className="flex min-h-[460px] flex-col gap-3 rounded-xl border border-border bg-card p-4">
          <div className="flex min-h-6 flex-wrap items-center gap-3 text-xs text-muted">
            {imageUrl ? (
              <>
                <span className="font-mono">
                  {naturalSize.w} x {naturalSize.h}px
                </span>
                {rotation !== 0 && (
                  <span className="text-accent">Rotate {rotation} deg</span>
                )}
                {activeTool !== "none" && (
                  <span className="text-accent">
                    Drag pada gambar untuk memilih area {activeTool}.
                  </span>
                )}
                {pipelineStages.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowPipelineModal(true)}
                    className="ml-auto flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent transition hover:bg-accent/20"
                  >
                    <Layers size={11} />
                    Lihat Pipeline Breakdown ({pipelineStages.length} tahap)
                  </button>
                )}
              </>
            ) : (
              <span>Upload gambar untuk mulai edit.</span>
            )}
          </div>

          <div
            className="relative flex flex-1 items-center justify-center overflow-hidden rounded-lg border border-border bg-[#0C1014]"
            onDrop={(event) => {
              event.preventDefault();
              const file = event.dataTransfer.files[0];
              if (file) handleFile(file);
            }}
            onDragOver={(event) => event.preventDefault()}
          >
            {!imageUrl ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center gap-3 px-6 py-10 text-center"
              >
                <span className="rounded-2xl border-2 border-dashed border-border p-5">
                  <ImageOff size={38} className="text-muted/50" />
                </span>
                <span className="text-sm font-semibold text-white">
                  Drag & drop atau klik Upload
                </span>
                <span className="text-xs text-muted">JPG, PNG, atau WebP</span>
              </button>
            ) : (
              <div
                ref={imageBoxRef}
                className="relative inline-flex max-h-[72vh] max-w-full select-none"
                style={{
                  cursor: activeTool === "none" ? "default" : "crosshair",
                }}
                onMouseDown={startSelection}
                onMouseMove={updateSelection}
                onMouseUp={finishSelection}
                onMouseLeave={finishSelection}
              >
                <img
                  ref={imgRef}
                  src={imageUrl}
                  alt="Editor canvas"
                  draggable={false}
                  onLoad={() => {
                    if (imgRef.current) {
                      setNaturalSize({
                        w: imgRef.current.naturalWidth,
                        h: imgRef.current.naturalHeight,
                      });
                    }
                  }}
                  className="max-h-[72vh] max-w-full object-contain"
                  style={{
                    filter: cssFilter,
                    opacity: state.opacity / 100,
                    transform: cssTransform,
                    transition: "filter 150ms ease, transform 180ms ease",
                  }}
                />

                {rect && rect.w > 4 && rect.h > 4 && (
                  <div
                    className="pointer-events-none absolute border-2 border-dashed border-accent bg-accent/10"
                    style={{
                      left: rect.x,
                      top: rect.y,
                      width: rect.w,
                      height: rect.h,
                    }}
                  />
                )}

                {isProcessing && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70">
                    <Loader2
                      size={32}
                      className="mb-3 animate-spin text-accent"
                    />
                    <p className="text-sm text-white">{processingText}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {rect && rect.w > 8 && rect.h > 8 && activeTool !== "none" && (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={activeTool === "crop" ? applyCrop : applyCutout}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-accent py-2 text-sm font-semibold text-[#0C1014] transition hover:bg-accent/90"
              >
                <Check size={15} />
                Apply {activeTool}
              </button>
              <button
                type="button"
                onClick={() => {
                  setRect(null);
                  setActiveTool("none");
                }}
                className="flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm text-muted transition hover:text-white"
              >
                <X size={15} />
                Cancel
              </button>
            </div>
          )}
        </div>

        <div className="space-y-3 rounded-xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted">
            Adjustments
          </p>
          <Slider
            label="Brightness"
            value={state.brightness}
            min={-100}
            max={100}
            onChange={(brightness) => patchState({ brightness })}
          />
          <Slider
            label="Contrast"
            value={state.contrast}
            min={-100}
            max={100}
            onChange={(contrast) => patchState({ contrast })}
          />
          <Slider
            label="Saturation"
            value={state.saturation}
            min={-100}
            max={100}
            onChange={(saturation) => patchState({ saturation })}
          />
          <Slider
            label="Hue"
            value={state.hue}
            min={-180}
            max={180}
            unit="deg"
            onChange={(hue) => patchState({ hue })}
          />
          <Slider
            label="Blur"
            value={state.blur}
            min={0}
            max={100}
            onChange={(blur) => patchState({ blur })}
          />
          <Slider
            label="Sharpness"
            value={state.sharpness}
            min={0}
            max={100}
            onChange={(sharpness) => patchState({ sharpness })}
          />
          <Slider
            label="Opacity"
            value={state.opacity}
            min={0}
            max={100}
            unit="%"
            onChange={(opacity) => patchState({ opacity })}
          />
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) handleFile(file);
          event.target.value = "";
        }}
      />

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm shadow-card ${
              toast.type === "ok"
                ? "border-green-500/40 bg-green-500/15 text-green-300"
                : "border-red-500/40 bg-red-500/15 text-red-300"
            }`}
          >
            {toast.type === "ok" ? (
              <Check size={15} />
            ) : (
              <AlertCircle size={15} />
            )}
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>

      <PipelineModal
        open={showPipelineModal}
        onClose={() => setShowPipelineModal(false)}
        stages={pipelineStages}
        method={pipelineMethod}
        coveragePct={pipelineCoverage}
        histogramBefore={pipelineHistBefore}
        histogramAfter={pipelineHistAfter}
      />
    </motion.div>
  );
}
