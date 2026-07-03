import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BlockMath } from "react-katex";
import "katex/dist/katex.min.css";
import {
  X,
  ChevronDown,
  ChevronUp,
  Target,
  BookOpen,
  Layers,
  Percent,
  BarChart3,
  Activity,
  ArrowRight,
} from "lucide-react";
import { HistogramChart } from "./ExplanationPanel";
import type { HistogramPayload } from "../api/imageApi";

interface StageMetrics {
  width: number;
  height: number;
  channels: number;
  mean: number;
  std: number;
  min: number;
  max: number;
  dark_pct: number;
  bright_pct: number;
  ink_pct: number;
  edge_density_pct: number;
}

interface StageChange {
  key: string;
  label: string;
  before: number;
  after: number;
  delta: number;
  unit?: string;
}

export interface PipelineStage {
  id: string;
  order: number;
  title: string;
  objective: string;
  formula: string;
  math_concept: string;
  description: string;
  image: string;
  secondary_image?: string;
  pixel_matrix?: number[][];
  pixel_matrix_before?: number[][];
  pixel_delta_matrix?: number[][];
  histogram?: HistogramPayload;
  metrics_before?: StageMetrics;
  metrics_after?: StageMetrics;
  changes?: StageChange[];
}

interface PipelineModalProps {
  open: boolean;
  onClose: () => void;
  stages: PipelineStage[];
  coveragePct?: number;
  method?: string;
  histogramBefore?: HistogramPayload;
  histogramAfter?: HistogramPayload;
}

function luminanceSeries(payload?: HistogramPayload) {
  if (!payload) return [];
  return Array.isArray(payload) ? payload : payload.luminance ?? [];
}

function histogramPath(data: number[], width: number, height: number) {
  if (!data.length) return "";
  return data
    .map((value, index) => {
      const normalized = Number.isFinite(value)
        ? Math.max(0, Math.min(1, value))
        : 0;
      const x = (index / Math.max(data.length - 1, 1)) * width;
      const y = height - normalized * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function MiniStageHistogram({ histogram }: { histogram?: HistogramPayload }) {
  const data = luminanceSeries(histogram);
  if (!data.length) return null;

  const width = 420;
  const height = 120;

  return (
    <div className="rounded-lg border border-border bg-[#0C1014] p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">
          <BarChart3 size={12} className="text-accent" /> Histogram Tahap
        </p>
        <span className="font-mono text-[10px] text-muted/70">luminance</span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="block h-28 w-full rounded border border-border/70 bg-[#090D11]"
      >
        {[0.25, 0.5, 0.75].map((ratio) => (
          <line
            key={ratio}
            x1="0"
            x2={width}
            y1={height * ratio}
            y2={height * ratio}
            stroke="#2A3340"
            strokeOpacity="0.5"
            strokeWidth="1"
          />
        ))}
        <path
          d={histogramPath(data, width, height)}
          fill="none"
          stroke="#E6E8EC"
          strokeWidth="2"
          strokeOpacity="0.92"
        />
      </svg>
      <div className="mt-1 flex justify-between font-mono text-[9px] text-muted/60">
        <span>0</span>
        <span>128</span>
        <span>255</span>
      </div>
    </div>
  );
}

function PixelMatrix({
  matrix,
  label = "Matriks Piksel 5x5",
  tone = "normal",
}: {
  matrix?: number[][];
  label?: string;
  tone?: "normal" | "delta";
}) {
  if (!matrix?.length) return null;

  return (
    <div className="rounded-lg border border-border bg-[#0C1014] p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">
          {label}
        </p>
        <span className="font-mono text-[10px] text-muted/70">
          {tone === "delta" ? "after-before" : "grayscale"}
        </span>
      </div>
      <div className="overflow-x-auto rounded border border-border/70">
        <div
          className="grid min-w-[260px] font-mono text-[11px] leading-none text-white/85"
          style={{
            gridTemplateColumns: `repeat(${matrix[0]?.length ?? 5}, minmax(48px, 1fr))`,
          }}
        >
          {matrix.flatMap((row, rowIndex) =>
            row.map((value, colIndex) => {
              const deltaClass =
                tone === "delta"
                  ? value > 0
                    ? "text-emerald-300 bg-emerald-500/[0.08]"
                    : value < 0
                      ? "text-rose-300 bg-rose-500/[0.08]"
                      : "text-muted bg-white/[0.02]"
                  : "bg-white/[0.025]";

              return (
                <div
                  key={`${rowIndex}-${colIndex}`}
                  className={`flex h-10 min-w-12 items-center justify-center whitespace-nowrap border-b border-r border-border/60 px-2 tabular-nums last:border-r-0 ${deltaClass}`}
                  title={`row ${rowIndex + 1}, col ${colIndex + 1}`}
                >
                  {tone === "delta" && value > 0 ? `+${value}` : value}
                </div>
              );
            }),
          )}
        </div>
      </div>
    </div>
  );
}

function formatChange(change: StageChange) {
  const unit = change.unit ?? "";
  const delta = change.delta > 0 ? `+${change.delta}` : String(change.delta);
  return `${delta}${unit}`;
}

function StageDataPanel({ stage }: { stage: PipelineStage }) {
  const metrics = stage.metrics_after;
  const changes = stage.changes ?? [];

  if (!metrics && !changes.length && !stage.histogram) return null;

  const metricCards = metrics
    ? [
        { label: "Resolusi", value: `${metrics.width}x${metrics.height}` },
        { label: "Mean", value: metrics.mean },
        { label: "Kontras", value: metrics.std },
        { label: "Edge", value: `${metrics.edge_density_pct}%` },
        { label: "Tinta", value: `${metrics.ink_pct}%` },
        { label: "Putih", value: `${metrics.bright_pct}%` },
      ]
    : [];

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_1.1fr]">
      <div className="rounded-lg border border-border bg-[#0C1014] p-3">
        <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">
          <Activity size={12} className="text-accent" /> Perubahan Data
        </p>
        {metricCards.length ? (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {metricCards.map((item) => (
              <div key={item.label} className="rounded border border-border/70 bg-white/[0.025] px-2.5 py-2">
                <p className="text-[10px] text-muted/70">{item.label}</p>
                <p className="font-mono text-xs font-semibold text-white">{item.value}</p>
              </div>
            ))}
          </div>
        ) : null}
        {changes.length ? (
          <div className="mt-3 space-y-1.5">
            {changes.map((change) => (
              <div
                key={change.key}
                className="flex items-center justify-between gap-3 rounded border border-border/50 bg-black/15 px-2.5 py-1.5 text-[11px]"
              >
                <span className="text-muted">{change.label}</span>
                <span className="flex items-center gap-1 font-mono text-white/85">
                  {change.before}{change.unit ?? ""}
                  <ArrowRight size={10} className="text-muted/60" />
                  {change.after}{change.unit ?? ""}
                  <span
                    className={
                      change.delta > 0
                        ? "text-emerald-300"
                        : change.delta < 0
                          ? "text-rose-300"
                          : "text-muted"
                    }
                  >
                    ({formatChange(change)})
                  </span>
                </span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
      <MiniStageHistogram histogram={stage.histogram} />
    </div>
  );
}

function StageCard({ stage }: { stage: PipelineStage }) {
  const [open, setOpen] = useState(stage.order <= 2);

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 transition-colors hover:bg-white/5"
      >
        <div className="flex items-center gap-3">
          <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-accent/40 bg-accent/15 font-mono text-xs font-bold text-accent">
            {stage.order}
          </span>
          <span className="text-left text-sm font-semibold text-white">
            {stage.title}
          </span>
        </div>
        {open ? (
          <ChevronUp size={14} className="flex-shrink-0 text-muted" />
        ) : (
          <ChevronDown size={14} className="flex-shrink-0 text-muted" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-5 px-5 pb-5 pt-2">
              <div className="flex items-start gap-2">
                <Target
                  size={13}
                  className="mt-0.5 flex-shrink-0 text-accent"
                />
                <p className="text-xs text-white/80">{stage.objective}</p>
              </div>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
                <div className="flex min-h-[260px] items-center justify-center overflow-hidden rounded-xl border border-border bg-[#0C1014] p-3">
                  <img
                    src={stage.image}
                    alt={stage.title}
                    className="max-h-[360px] max-w-full object-contain"
                  />
                </div>
                <div className="space-y-3">
                  <div className="overflow-x-auto rounded-lg border border-border bg-[#0C1014] p-3">
                    <BlockMath math={stage.formula} />
                  </div>
                  {stage.secondary_image && (
                    <div className="flex items-center justify-center overflow-hidden rounded-lg border border-border bg-[#0C1014]">
                      <img
                        src={stage.secondary_image}
                        alt={`${stage.title} secondary`}
                        className="max-h-28 max-w-full object-contain"
                      />
                    </div>
                  )}

                </div>
              </div>

              <StageDataPanel stage={stage} />

              <div className="rounded-xl border border-border bg-[#0C1014]/80 p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                      Matriks Piksel
                    </p>
                    <p className="mt-1 text-[11px] leading-relaxed text-muted/70">
                      Sampel 5x5 dibuat lebih lega agar nilai 0-255 dan delta perubahan tidak saling menimpa.
                    </p>
                  </div>
                  <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10px] text-muted/70">
                    top-left sample
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                  <PixelMatrix
                    matrix={stage.pixel_matrix_before}
                    label="Sebelum Operasi"
                  />
                  <PixelMatrix matrix={stage.pixel_matrix} label="Sesudah Operasi" />
                  <PixelMatrix
                    matrix={stage.pixel_delta_matrix}
                    label="Delta Perubahan"
                    tone="delta"
                  />
                </div>
              </div>

              <div className="flex items-start gap-2 rounded-lg border border-accent/20 bg-accent/5 p-3">
                <BookOpen
                  size={13}
                  className="mt-0.5 flex-shrink-0 text-accent"
                />
                <p className="text-xs leading-relaxed text-muted">
                  {stage.math_concept}
                </p>
              </div>

              <p className="px-1 font-mono text-[11px] text-muted/70">
                {stage.description}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function PipelineModal({
  open,
  onClose,
  stages,
  coveragePct,
  method,
  histogramBefore,
  histogramAfter,
}: PipelineModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="pipeline-modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            key="pipeline-modal-panel"
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.25 }}
            onClick={(event) => event.stopPropagation()}
            className="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-border bg-bg shadow-card"
          >
            <div className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card px-5 py-4">
              <div className="flex items-center gap-2.5">
                <Layers size={18} className="text-accent" />
                <div>
                  <h3
                    className="text-base font-bold text-white"
                    style={{ fontFamily: "'Playfair Display',serif" }}
                  >
                    Pipeline Breakdown
                  </h3>
                  <p className="text-[11px] text-muted">
                    {method ?? "Computer Vision Pipeline"} - {stages.length} tahap
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {typeof coveragePct === "number" && (
                  <span className="flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 font-mono text-xs text-accent">
                    <Percent size={11} /> {coveragePct}% foreground
                  </span>
                )}
                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 transition-colors hover:bg-white/10"
                >
                  <X size={16} className="text-muted hover:text-white" />
                </button>
              </div>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
              <p className="pb-1 text-xs leading-relaxed text-muted">
                Pipeline ini memperlihatkan tahapan pengolahan citra dari input
                sampai output akhir. Setiap tahap menampilkan tujuan, formula,
                konsep, parameter, histogram tahap, metrik perubahan, matriks piksel, dan preview hasil antara.
              </p>

              {[...stages]
                .sort((a, b) => a.order - b.order)
                .map((stage) => (
                  <StageCard key={stage.id} stage={stage} />
                ))}

              {histogramBefore || histogramAfter ? (
                <div className="mt-4 rounded-xl border border-border bg-card p-4">
                  <p className="mb-3 text-sm font-semibold text-white">
                    Distribusi Intensitas
                  </p>
                  <HistogramChart
                    before={histogramBefore}
                    after={histogramAfter}
                  />
                </div>
              ) : null}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
