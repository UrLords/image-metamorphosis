import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  AlertCircle,
  Check,
  Download,
  FileImage,
  Layers,
  Loader2,
  RefreshCw,
  ScanLine,
  Settings2,
  UploadCloud,
} from "lucide-react";
import apiClient from "../api/axiosClient";
import { HistogramChart } from "../components/ExplanationPanel";
import PipelineModal, { type PipelineStage } from "../components/PipelineModal";
import type { HistogramPayload } from "../api/imageApi";

type ScanMode = "bw" | "clean" | "grayscale" | "color";
type ScanPreset = "document" | "receipt" | "id";
type EnhanceLevel = "soft" | "balanced" | "strong";
type PaperSize = "auto" | "a4" | "letter" | "keep";

interface ScanResult {
  bw: string;
  clean: string;
  grayscale: string;
  color: string;
  stages: PipelineStage[];
  doc_detected: boolean;
  detection_score: number;
  output_resolution: string;
  histogram_before: HistogramPayload;
  histogram_after: HistogramPayload;
  method: string;
}

const MODE_LABELS: { mode: ScanMode; label: string; desc: string }[] = [
  {
    mode: "bw",
    label: "B/W Sharp",
    desc: "Teks paling tegas untuk dokumen.",
  },
  {
    mode: "clean",
    label: "Clean Text",
    desc: "Lebih halus untuk catatan dan surat.",
  },
  {
    mode: "grayscale",
    label: "Grayscale",
    desc: "Detail kertas tetap natural.",
  },
  {
    mode: "color",
    label: "Color",
    desc: "Warna dipertahankan dan dirapikan.",
  },
];

const PRESET_LABELS: { value: ScanPreset; label: string }[] = [
  { value: "document", label: "Document" },
  { value: "receipt", label: "Receipt / Nota" },
  { value: "id", label: "ID Card" },
];

const ENHANCE_LABELS: { value: EnhanceLevel; label: string }[] = [
  { value: "soft", label: "Soft" },
  { value: "balanced", label: "Balanced" },
  { value: "strong", label: "Strong" },
];

const PAPER_LABELS: { value: PaperSize; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "a4", label: "A4" },
  { value: "letter", label: "Letter" },
  { value: "keep", label: "Keep Shape" },
];

function SelectControl<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[11px] font-semibold uppercase tracking-widest text-muted">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="rounded-lg border border-border bg-[#0C1014] px-3 py-2 text-sm text-white outline-none transition focus:border-accent"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ScanDocument() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [activeMode, setActiveMode] = useState<ScanMode>("bw");
  const [preset, setPreset] = useState<ScanPreset>("document");
  const [enhance, setEnhance] = useState<EnhanceLevel>("balanced");
  const [paperSize, setPaperSize] = useState<PaperSize>("auto");
  const [outputMax, setOutputMax] = useState(1800);
  const [autoCrop, setAutoCrop] = useState(true);
  const [isProcessing, setProcessing] = useState(false);
  const [toast, setToast] = useState<{
    msg: string;
    type: "ok" | "err";
  } | null>(null);
  const [showPipeline, setShowPipeline] = useState(false);
  const downloadRef = useRef<HTMLAnchorElement>(null);

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type });
    window.setTimeout(() => setToast(null), 3500);
  };

  const onDrop = useCallback((files: File[]) => {
    const file = files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setImageUrl(reader.result as string);
      setResult(null);
    };
    reader.readAsDataURL(file);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"] },
    maxFiles: 1,
  });

  const handleScan = async () => {
    if (!imageUrl) return;
    setProcessing(true);
    try {
      const res = await apiClient.post<ScanResult>("/editor/scan-document", {
        image: imageUrl,
        options: {
          preset,
          enhance,
          paper_size: paperSize,
          output_max: outputMax,
          auto_crop: autoCrop,
        },
      });
      setResult(res.data);
      setActiveMode("bw");
      showToast(
        res.data.doc_detected
          ? `Document detected. ${res.data.output_resolution}`
          : "Document edge not detected. Full frame was processed.",
        "ok",
      );
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string } } };
      const msg =
        err.response?.data?.error ||
        (e instanceof Error ? e.message : String(e));
      showToast("Failed: " + msg, "err");
    } finally {
      setProcessing(false);
    }
  };

  const handleDownload = async (format: "png" | "jpg") => {
    if (!result) return;
    const src = result[activeMode];
    const link = downloadRef.current;
    if (!link) return;

    if (format === "png") {
      link.href = src;
      link.download = `scan_${activeMode}.png`;
      link.click();
      showToast("PNG downloaded.");
      return;
    }

    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      link.href = canvas.toDataURL("image/jpeg", 0.94);
      link.download = `scan_${activeMode}.jpg`;
      link.click();
      showToast("JPG downloaded.");
    };
    image.src = src;
  };

  const resetScan = () => {
    setImageUrl(null);
    setResult(null);
  };

  const displaySrc = result ? result[activeMode] : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-6xl space-y-6"
    >
      <div className="border-b border-border pb-4">
        <div className="mb-1 flex items-center gap-3">
          <div className="rounded-lg border border-accent/20 bg-accent/10 p-2">
            <ScanLine size={18} className="text-accent" />
          </div>
          <h2
            className="text-2xl font-bold text-white"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Scan Dokumen
          </h2>
        </div>
        <p className="ml-12 text-sm text-muted">
          Koreksi perspektif, bersihkan bayangan, perjelas teks, dan ekspor
          hasil scan dalam beberapa mode.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-4">
          <div
            {...getRootProps()}
            className={`flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-5 text-center transition-all ${
              isDragActive
                ? "border-accent bg-accent/5"
                : "border-border bg-card hover:border-accent/40"
            }`}
          >
            <input {...getInputProps()} />
            {imageUrl ? (
              <div className="w-full">
                <img
                  src={imageUrl}
                  alt="Input"
                  className="max-h-48 w-full rounded-lg object-contain"
                />
                <p className="mt-2 text-xs text-muted">
                  Klik atau drag untuk mengganti gambar
                </p>
              </div>
            ) : (
              <>
                <div className="rounded-full border border-dashed border-border bg-[#0C1014] p-3">
                  <UploadCloud size={26} className="text-accent/70" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    {isDragActive ? "Lepas di sini" : "Upload foto dokumen"}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Kertas, nota, kartu, surat, atau catatan.
                  </p>
                </div>
              </>
            )}
          </div>

          <div className="space-y-4 rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2">
              <Settings2 size={15} className="text-accent" />
              <p className="text-xs font-semibold uppercase tracking-widest text-white">
                Scanner Settings
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3">
              <SelectControl
                label="Preset"
                value={preset}
                options={PRESET_LABELS}
                onChange={setPreset}
              />
              <SelectControl
                label="Enhancement"
                value={enhance}
                options={ENHANCE_LABELS}
                onChange={setEnhance}
              />
              <SelectControl
                label="Paper"
                value={paperSize}
                options={PAPER_LABELS}
                onChange={setPaperSize}
              />
            </div>

            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">
                Output Size
              </p>
              <div className="grid grid-cols-3 gap-2">
                {[1200, 1800, 2400].map((size) => (
                  <button
                    key={size}
                    onClick={() => setOutputMax(size)}
                    className={`rounded-lg border px-2 py-2 text-xs font-semibold transition ${
                      outputMax === size
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border bg-[#0C1014] text-muted hover:border-accent/40"
                    }`}
                  >
                    {size}px
                  </button>
                ))}
              </div>
            </div>

            <label className="flex items-center justify-between gap-3 rounded-lg border border-border bg-[#0C1014] px-3 py-2">
              <span className="text-xs text-white">Auto crop & deskew</span>
              <input
                type="checkbox"
                checked={autoCrop}
                onChange={(event) => setAutoCrop(event.target.checked)}
                className="h-4 w-4 accent-[#C9A86C]"
              />
            </label>
          </div>

          <button
            onClick={handleScan}
            disabled={!imageUrl || isProcessing}
            className={`flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold transition-all ${
              !imageUrl || isProcessing
                ? "cursor-not-allowed bg-accent/20 text-accent/40"
                : "bg-accent text-[#0C1014] shadow-glow hover:bg-accent/90 active:scale-[0.98]"
            }`}
          >
            {isProcessing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Processing scanner pipeline...
              </>
            ) : (
              <>
                <ScanLine size={16} />
                Scan Document
              </>
            )}
          </button>

          {result && (
            <div className="space-y-2">
              <button
                onClick={() => setShowPipeline(true)}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-accent/30 bg-accent/5 py-2.5 text-sm text-accent transition hover:bg-accent/10"
              >
                <Layers size={14} />
                Pipeline Breakdown ({result.stages.length} tahap)
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleDownload("png")}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-border bg-card py-2 text-sm text-muted transition hover:border-accent/40 hover:text-white"
                >
                  <Download size={13} /> PNG
                </button>
                <button
                  onClick={() => handleDownload("jpg")}
                  className="flex items-center justify-center gap-1.5 rounded-lg bg-accent py-2 text-sm font-semibold text-[#0C1014] transition hover:bg-accent/90"
                >
                  <Download size={13} /> JPG
                </button>
              </div>
              <button
                onClick={resetScan}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/5 py-2 text-sm text-red-400 transition hover:bg-red-500/10"
              >
                <RefreshCw size={13} /> Scan Ulang
              </button>
            </div>
          )}
        </div>

        <div className="space-y-4">
          {result && (
            <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
              {MODE_LABELS.map(({ mode, label, desc }) => (
                <button
                  key={mode}
                  onClick={() => setActiveMode(mode)}
                  className={`rounded-xl border p-3 text-left transition-all ${
                    activeMode === mode
                      ? "border-accent bg-accent/10"
                      : "border-border bg-card hover:border-accent/30"
                  }`}
                >
                  <p
                    className={`text-xs font-semibold ${
                      activeMode === mode ? "text-accent" : "text-white"
                    }`}
                  >
                    {label}
                  </p>
                  <p className="mt-0.5 text-[10px] text-muted">{desc}</p>
                </button>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full bg-muted" />
                <span className="text-xs font-medium uppercase tracking-widest text-muted">
                  Sebelum
                </span>
              </div>
              <div className="flex min-h-72 items-center justify-center overflow-hidden rounded-xl border border-border bg-card">
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt="Before"
                    className="max-h-[520px] w-full object-contain"
                  />
                ) : (
                  <div className="flex flex-col items-center gap-2 py-12 text-muted">
                    <FileImage size={32} className="opacity-30" />
                    <p className="text-xs">Upload gambar dulu</p>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full bg-accent" />
                <span className="text-xs font-medium uppercase tracking-widest text-accent">
                  Sesudah{" "}
                  {result
                    ? MODE_LABELS.find((item) => item.mode === activeMode)
                        ?.label
                    : ""}
                </span>
              </div>
              <div className="relative flex min-h-72 items-center justify-center overflow-hidden rounded-xl border border-accent/30 bg-card">
                {isProcessing ? (
                  <div className="flex flex-col items-center gap-3 py-12">
                    <Loader2 size={32} className="animate-spin text-accent" />
                    <p className="text-xs text-accent">
                      Scanner pipeline sedang berjalan...
                    </p>
                  </div>
                ) : displaySrc ? (
                  <motion.img
                    key={activeMode}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    src={displaySrc}
                    alt="After"
                    className="max-h-[520px] w-full object-contain"
                  />
                ) : (
                  <div className="flex flex-col items-center gap-2 py-12 text-muted">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full border border-dashed border-muted/30">
                      <span className="text-lg text-muted/30">?</span>
                    </div>
                    <p className="text-xs">Hasil akan muncul di sini</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {result && (
            <div className="flex flex-wrap items-center gap-3 px-1 text-xs text-muted">
              <span className="font-mono">{result.output_resolution}</span>
              <span className="font-mono">
                score {result.detection_score.toFixed(2)}
              </span>
              {result.doc_detected ? (
                <span className="flex items-center gap-1 text-green-400">
                  <Check size={11} /> Dokumen terdeteksi dan diluruskan
                </span>
              ) : (
                <span className="flex items-center gap-1 text-yellow-400">
                  <AlertCircle size={11} /> Tepi tidak terdeteksi, frame penuh
                  diproses
                </span>
              )}
            </div>
          )}

          {result && (
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="mb-3 text-sm font-semibold text-white">
                Distribusi Intensitas
              </p>
              <HistogramChart
                before={result.histogram_before}
                after={result.histogram_after}
              />
            </div>
          )}

          {!result && !isProcessing && (
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="mb-3 text-sm font-semibold text-white">
                Tips Foto Scanner
              </p>
              <ul className="space-y-2 text-xs leading-relaxed text-muted">
                <li>Pastikan semua sudut dokumen terlihat.</li>
                <li>Gunakan background yang kontras dengan warna kertas.</li>
                <li>Hindari pantulan cahaya keras di atas teks.</li>
                <li>Pakai Strong enhancement untuk foto gelap atau banyak bayangan.</li>
                <li>Matikan auto-crop jika ingin memproses seluruh foto.</li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {result && (
        <PipelineModal
          open={showPipeline}
          onClose={() => setShowPipeline(false)}
          stages={result.stages}
          method={result.method}
          histogramBefore={result.histogram_before}
          histogramAfter={result.histogram_after}
        />
      )}

      <AnimatePresence>
        {toast && (
          <motion.div
            key="toast"
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 32 }}
            className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium shadow-card ${
              toast.type === "ok"
                ? "border-green-500/40 bg-green-500/15 text-green-300"
                : "border-red-500/40 bg-red-500/15 text-red-300"
            }`}
          >
            {toast.type === "ok" ? (
              <Check size={14} />
            ) : (
              <AlertCircle size={14} />
            )}
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      <a ref={downloadRef} className="hidden" />
    </motion.div>
  );
}
