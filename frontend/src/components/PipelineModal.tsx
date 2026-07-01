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
} from "lucide-react";
import { HistogramChart } from "./ExplanationPanel";
import type { HistogramPayload } from "../api/imageApi";

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

function PixelMatrix({ matrix }: { matrix?: number[][] }) {
  if (!matrix?.length) return null;

  return (
    <div className="rounded-lg border border-border bg-[#0C1014] p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">
          Matriks Piksel 5x5
        </p>
        <span className="font-mono text-[10px] text-muted/70">grayscale</span>
      </div>
      <div className="grid grid-cols-5 overflow-hidden rounded border border-border/70 font-mono text-[10px] text-white/80">
        {matrix.flatMap((row, rowIndex) =>
          row.map((value, colIndex) => (
            <div
              key={`${rowIndex}-${colIndex}`}
              className="flex h-7 items-center justify-center border-b border-r border-border/60 bg-white/[0.025] last:border-r-0"
              title={`row ${rowIndex + 1}, col ${colIndex + 1}`}
            >
              {value}
            </div>
          )),
        )}
      </div>
      <p className="mt-2 text-[10px] leading-relaxed text-muted/70">
        Sampel nilai intensitas piksel dari area kiri-atas hasil tahap ini.
      </p>
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
            <div className="space-y-3 px-4 pb-4 pt-1">
              <div className="flex items-start gap-2">
                <Target
                  size={13}
                  className="mt-0.5 flex-shrink-0 text-accent"
                />
                <p className="text-xs text-white/80">{stage.objective}</p>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="flex min-h-[140px] items-center justify-center overflow-hidden rounded-lg border border-border bg-[#0C1014]">
                  <img
                    src={stage.image}
                    alt={stage.title}
                    className="max-h-48 max-w-full object-contain"
                  />
                </div>
                <div className="space-y-2">
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
                  <PixelMatrix matrix={stage.pixel_matrix} />
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
            className="flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-border bg-bg shadow-card"
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

            <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
              <p className="pb-1 text-xs leading-relaxed text-muted">
                Pipeline ini memperlihatkan tahapan pengolahan citra dari input
                sampai output akhir. Setiap tahap menampilkan tujuan, formula,
                konsep, parameter, matriks piksel, dan preview hasil antara.
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
