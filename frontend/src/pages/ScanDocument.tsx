// src/pages/ScanDocument.tsx
// Halaman restorasi dokumen bergaya CamScanner - terpisah dari Advanced Editor.
import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  FileImage, Download, Layers, RefreshCw, Loader2,
  AlertCircle, Check, UploadCloud, ScanLine,
} from "lucide-react";
import apiClient from "../api/axiosClient";
import { BlockMath } from "react-katex";
import "katex/dist/katex.min.css";
import { HistogramChart } from "../components/ExplanationPanel";
import PipelineModal, { type PipelineStage } from "../components/PipelineModal";
import type { HistogramPayload } from "../api/imageApi";

type ScanMode = "bw" | "grayscale" | "color";

interface ScanResult {
  bw: string;
  grayscale: string;
  color: string;
  stages: PipelineStage[];
  doc_detected: boolean;
  output_resolution: string;
  histogram_before: HistogramPayload;
  histogram_after: HistogramPayload;
  method: string;
}

const MODE_LABELS: { mode: ScanMode; label: string; desc: string }[] = [
  { mode: "bw",        label: "Hitam-Putih",    desc: "Seperti hasil scan - kontras tinggi" },
  { mode: "grayscale", label: "Grayscale",       desc: "Bayangan halus tetap terlihat" },
  { mode: "color",     label: "Warna Enhanced",  desc: "Warna asli + noda kopi direduksi" },
];

export default function ScanDocument() {
  const [imageUrl, setImageUrl]       = useState<string | null>(null);
  const [result, setResult]           = useState<ScanResult | null>(null);
  const [activeMode, setActiveMode]   = useState<ScanMode>("bw");
  const [isProcessing, setProcessing] = useState(false);
  const [toast, setToast]             = useState<{ msg: string; type: "ok" | "err" } | null>(null);
  const [showPipeline, setShowPipeline] = useState(false);
  const downloadRef = useRef<HTMLAnchorElement>(null);

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  // Upload
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

  // Process
  const handleScan = async () => {
    if (!imageUrl) return;
    setProcessing(true);
    try {
      const res = await apiClient.post<ScanResult>("/editor/scan-document", { image: imageUrl });
      setResult(res.data);
      setActiveMode("bw");
      showToast(
        res.data.doc_detected
          ? `Dokumen terdeteksi & diluruskan OK - ${res.data.output_resolution}`
          : "Tepi dokumen tidak terdeteksi - frame penuh diproses.",
        res.data.doc_detected ? "ok" : "ok",
      );
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string } } };
      const msg = err.response?.data?.error || (e instanceof Error ? e.message : String(e));
      showToast("Gagal: " + msg, "err");
    } finally {
      setProcessing(false);
    }
  };

  // Download
  const handleDownload = (format: "png" | "jpg") => {
    if (!result) return;
    const src = result[activeMode];
    const a = downloadRef.current!;
    a.href = src;
    a.download = `scan_${activeMode}.${format}`;
    a.click();
    showToast(`Download ${format.toUpperCase()} selesai OK`);
  };

  const displaySrc = result ? result[activeMode] : null;

  // Render
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-lg bg-accent/10 border border-accent/20">
            <ScanLine size={18} className="text-accent" />
          </div>
          <h2
            className="text-2xl font-bold text-white"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Scan Dokumen
          </h2>
        </div>
        <p className="text-sm text-muted ml-12">
          Foto kertas / dokumen diproses otomatis: dideteksi, diluruskan perspektif, dihilangkan bayangan & noda,
          diperjelas teksnya. Pipeline 8 tahap OpenCV - seperti CamScanner.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* LEFT: Upload + Controls */}
        <div className="space-y-4">

          {/* Upload zone */}
          <div
            {...getRootProps()}
            className={`rounded-xl border-2 border-dashed cursor-pointer transition-all p-5 flex flex-col items-center gap-3 text-center
              ${isDragActive ? "border-accent bg-accent/5" : "border-border bg-card hover:border-accent/40"}`}
          >
            <input {...getInputProps()} />
            {imageUrl ? (
              <div className="w-full">
                <img src={imageUrl} alt="Input" className="w-full max-h-48 object-contain rounded-lg" />
                <p className="text-xs text-muted mt-2">Klik / drag untuk ganti gambar</p>
              </div>
            ) : (
              <>
                <div className="p-3 rounded-full border border-dashed border-border bg-[#0C1014]">
                  <UploadCloud size={26} className="text-accent/70" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    {isDragActive ? "Lepas di sini!" : "Upload foto dokumen"}
                  </p>
                  <p className="text-xs text-muted mt-1">
                    Foto kertas, KTP, KK, surat, nota - JPG / PNG / WebP
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Pipeline info */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-2">
            <p className="text-xs font-semibold text-white uppercase tracking-widest">Pipeline (8 Tahap)</p>
            {[
              "Grayscale + Gaussian Blur",
              "Canny Edge Detection",
              "Contour + Quad Detection",
              "Perspective Transform (Deskew)",
              "Shadow + Stain Removal",
              "Noise Reduction",
              "Sharpening",
              "Adaptive Thresholding",
            ].map((s, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-accent/15 border border-accent/30 text-accent text-[10px] font-mono flex items-center justify-center flex-shrink-0">
                  {i + 1}
                </span>
                <span className="text-xs text-muted">{s}</span>
              </div>
            ))}
          </div>

          {/* Process button */}
          <button
            onClick={handleScan}
            disabled={!imageUrl || isProcessing}
            className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all
              ${!imageUrl || isProcessing
                ? "bg-accent/20 text-accent/40 cursor-not-allowed"
                : "bg-accent text-[#0C1014] hover:bg-accent/90 shadow-glow active:scale-[0.98]"}`}
          >
            {isProcessing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Memproses 8 tahap...
              </>
            ) : (
              <>
                <ScanLine size={16} />
                Scan & Restore Dokumen
              </>
            )}
          </button>

          {/* Actions after result */}
          {result && (
            <div className="space-y-2">
              <button
                onClick={() => setShowPipeline(true)}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-accent/30 bg-accent/5 text-accent text-sm hover:bg-accent/10 transition"
              >
                <Layers size={14} />
                Lihat Pipeline Breakdown ({result.stages.length} tahap)
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleDownload("png")}
                  className="flex items-center justify-center gap-1.5 py-2 rounded-lg border border-border bg-card text-sm text-muted hover:text-white hover:border-accent/40 transition"
                >
                  <Download size={13} /> PNG
                </button>
                <button
                  onClick={() => handleDownload("jpg")}
                  className="flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent text-[#0C1014] text-sm font-semibold hover:bg-accent/90 transition"
                >
                  <Download size={13} /> JPG
                </button>
              </div>
              <button
                onClick={() => { setImageUrl(null); setResult(null); }}
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border border-red-500/20 bg-red-500/5 text-red-400 text-sm hover:bg-red-500/10 transition"
              >
                <RefreshCw size={13} /> Scan Ulang
              </button>
            </div>
          )}
        </div>

        {/* RIGHT: Result area */}
        <div className="lg:col-span-2 space-y-4">

          {/* Mode switcher */}
          {result && (
            <div className="grid grid-cols-3 gap-2">
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
                  <p className={`text-xs font-semibold ${activeMode === mode ? "text-accent" : "text-white"}`}>
                    {label}
                  </p>
                  <p className="text-[10px] text-muted mt-0.5">{desc}</p>
                </button>
              ))}
            </div>
          )}

          {/* Before / After */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Before */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-muted" />
                <span className="text-xs font-medium text-muted uppercase tracking-widest">Sebelum (Input)</span>
              </div>
              <div className="rounded-xl border border-border bg-card min-h-48 flex items-center justify-center overflow-hidden">
                {imageUrl ? (
                  <img src={imageUrl} alt="Before" className="w-full max-h-72 object-contain" />
                ) : (
                  <div className="text-muted flex flex-col items-center gap-2 py-12">
                    <FileImage size={32} className="opacity-30" />
                    <p className="text-xs">Upload gambar dulu</p>
                  </div>
                )}
              </div>
            </div>

            {/* After */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-accent" />
                <span className="text-xs font-medium text-accent uppercase tracking-widest">
                  Sesudah {result ? `- ${MODE_LABELS.find(m => m.mode === activeMode)?.label}` : ""}
                </span>
              </div>
              <div className="rounded-xl border border-accent/30 bg-card min-h-48 flex items-center justify-center overflow-hidden relative">
                {isProcessing ? (
                  <div className="flex flex-col items-center gap-3 py-12">
                    <Loader2 size={32} className="text-accent animate-spin" />
                    <p className="text-xs text-accent">Pipeline sedang berjalan...</p>
                  </div>
                ) : displaySrc ? (
                  <motion.img
                    key={activeMode}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    src={displaySrc}
                    alt="After"
                    className="w-full max-h-72 object-contain"
                  />
                ) : (
                  <div className="text-muted flex flex-col items-center gap-2 py-12">
                    <div className="w-10 h-10 rounded-full border border-dashed border-muted/30 flex items-center justify-center">
                      <span className="text-muted/30 text-lg">?</span>
                    </div>
                    <p className="text-xs">Hasil akan muncul di sini</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Resolution + detection status */}
          {result && (
            <div className="flex items-center gap-3 flex-wrap text-xs text-muted px-1">
              <span className="font-mono">{result.output_resolution}</span>
              {result.doc_detected
                ? <span className="text-green-400 flex items-center gap-1"><Check size={11} /> Dokumen terdeteksi & diluruskan</span>
                : <span className="text-yellow-400 flex items-center gap-1"><AlertCircle size={11} /> Tepi tidak terdeteksi - frame penuh</span>
              }
            </div>
          )}

          {/* Histogram */}
          {result && (
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-sm font-semibold text-white mb-3">
                Distribusi Intensitas - Before vs After
              </p>
              <HistogramChart
                before={result.histogram_before}
                after={result.histogram_after}
              />
            </div>
          )}

          {/* Info box when no result yet */}
          {!result && !isProcessing && (
            <div className="rounded-xl border border-border bg-card p-5 space-y-3">
              <p className="text-sm font-semibold text-white">Tips Tips Foto Terbaik</p>
              <ul className="space-y-2 text-xs text-muted">
                <li className="flex items-start gap-2">
                  <span className="text-accent flex-shrink-0 mt-0.5">OK</span>
                  Foto di bawah cahaya cukup (jangan terlalu gelap/silau)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent flex-shrink-0 mt-0.5">OK</span>
                  Letakkan dokumen di atas permukaan kontras (mis: meja gelap untuk kertas putih)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent flex-shrink-0 mt-0.5">OK</span>
                  Semua 4 sudut dokumen harus kelihatan di foto
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent flex-shrink-0 mt-0.5">OK</span>
                  Noda kopi / bayangan ringan bisa direduksi secara otomatis
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-yellow-400 flex-shrink-0 mt-0.5">!</span>
                  Teks yang tertutup noda tinta gelap total tidak bisa dipulihkan
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline breakdown modal */}
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

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            key="toast"
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 32 }}
            className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium shadow-card
              ${toast.type === "ok"
                ? "border-green-500/40 bg-green-500/15 text-green-300"
                : "border-red-500/40 bg-red-500/15 text-red-300"}`}
          >
            {toast.type === "ok" ? <Check size={14} /> : <AlertCircle size={14} />}
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hidden download anchor */}
      <a ref={downloadRef} className="hidden" />
    </motion.div>
  );
}

