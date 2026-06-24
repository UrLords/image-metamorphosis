// src/components/PipelineModal.tsx
// Modal edukasi: breakdown pipeline segmentasi CV klasik
// dipakai oleh Advanced Editor setelah Remove BG / Object Cutout.
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BlockMath } from "react-katex";
import "katex/dist/katex.min.css";
import {
  X, ChevronDown, ChevronUp, Target, BookOpen, Layers, Percent,
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

function StageCard({ stage }: { stage: PipelineStage }) {
  const [open, setOpen] = useState(stage.order <= 2);

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="flex-shrink-0 w-7 h-7 rounded-full bg-accent/15 border border-accent/40 text-accent text-xs font-mono font-bold flex items-center justify-center">
            {stage.order}
          </span>
          <span className="text-sm font-semibold text-white text-left">{stage.title}</span>
        </div>
        {open ? <ChevronUp size={14} className="text-muted flex-shrink-0" /> : <ChevronDown size={14} className="text-muted flex-shrink-0" />}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }} className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 space-y-3">
              {/* Objective */}
              <div className="flex items-start gap-2">
                <Target size={13} className="text-accent mt-0.5 flex-shrink-0" />
                <p className="text-xs text-white/80">{stage.objective}</p>
              </div>

              {/* Image preview(s) + Formula side by side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="rounded-lg overflow-hidden border border-border bg-[#0C1014] flex items-center justify-center min-h-[140px]">
                  <img src={stage.image} alt={stage.title} className="max-w-full max-h-48 object-contain" />
                </div>
                <div className="space-y-2">
                  <div className="bg-[#0C1014] rounded-lg p-3 overflow-x-auto border border-border">
                    <BlockMath math={stage.formula} />
                  </div>
                  {stage.secondary_image && (
                    <div className="rounded-lg overflow-hidden border border-border bg-[#0C1014] flex items-center justify-center">
                      <img src={stage.secondary_image} alt={`${stage.title} secondary`} className="max-w-full max-h-28 object-contain" />
                    </div>
                  )}
                </div>
              </div>

              {/* Math concept */}
              <div className="flex items-start gap-2 bg-accent/5 border border-accent/20 rounded-lg p-3">
                <BookOpen size={13} className="text-accent mt-0.5 flex-shrink-0" />
                <p className="text-xs text-muted leading-relaxed">{stage.math_concept}</p>
              </div>

              {/* Description / params */}
              <p className="text-[11px] text-muted/70 font-mono px-1">{stage.description}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function PipelineModal({
  open, onClose, stages, coveragePct, method, histogramBefore, histogramAfter,
}: PipelineModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="pipeline-modal-backdrop"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div
            key="pipeline-modal-panel"
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.25 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-3xl max-h-[88vh] flex flex-col rounded-2xl border border-border bg-bg shadow-card overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-card flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <Layers size={18} className="text-accent" />
                <div>
                  <h3 className="text-base font-bold text-white" style={{ fontFamily: "'Playfair Display',serif" }}>
                    Pipeline Breakdown
                  </h3>
                  <p className="text-[11px] text-muted">{method ?? "OpenCV Processing Pipeline"} - {stages.length} tahap</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {typeof coveragePct === "number" && (
                  <span className="flex items-center gap-1 text-xs font-mono text-accent bg-accent/10 border border-accent/30 px-2.5 py-1 rounded-full">
                    <Percent size={11} /> {coveragePct}% foreground
                  </span>
                )}
                <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                  <X size={16} className="text-muted hover:text-white" />
                </button>
              </div>
            </div>

            {/* Body - scrollable */}
            <div className="overflow-y-auto px-5 py-4 space-y-3 flex-1">
              <p className="text-xs text-muted leading-relaxed pb-1">
                Sistem ini memakai pipeline OpenCV klasik untuk memperlihatkan proses pengolahan citra tahap demi tahap. Klik tiap tahap untuk melihat formula, konsep matematis, dan hasil antara.
              </p>

              {[...stages].sort((a, b) => a.order - b.order).map((s) => (
                <StageCard key={s.id} stage={s} />
              ))}

              {(histogramBefore || histogramAfter) ? (
                <div className="rounded-xl border border-border bg-card p-4 mt-4">
                  <p className="text-sm font-semibold text-white mb-3">Histogram RGB dan Luminance: Asli vs Hasil</p>
                  <HistogramChart before={histogramBefore} after={histogramAfter} />
                </div>
              ) : null}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

