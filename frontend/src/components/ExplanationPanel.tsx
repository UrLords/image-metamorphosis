// src/components/ExplanationPanel.tsx
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { InlineMath, BlockMath } from "react-katex";
import "katex/dist/katex.min.css";
import {
  ChevronDown,
  ChevronUp,
  BookOpen,
  Grid,
  Code2,
  Cpu,
  BarChart3,
} from "lucide-react";
import type { Explanation } from "../api/imageApi";

// ── Sub-components ─────────────────────────────────────────────

function SectionCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/2 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon size={15} className="text-accent" />
          <span className="text-sm font-semibold text-white">{title}</span>
        </div>
        {open ? (
          <ChevronUp size={14} className="text-muted" />
        ) : (
          <ChevronDown size={14} className="text-muted" />
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
            <div className="px-4 pb-4 pt-1">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PixelMatrix({ data, label }: { data: number[][]; label?: string }) {
  // Color-code by intensity
  const getColor = (v: number) => {
    const intensity = Math.round(v);
    return `rgb(${intensity},${intensity},${intensity})`;
  };

  return (
    <div>
      {label && <p className="text-xs text-muted mb-2">{label}</p>}
      <div className="overflow-x-auto">
        <table className="pixel-matrix border-collapse">
          <tbody>
            {data.map((row, r) => (
              <tr key={r}>
                {row.map((val, c) => (
                  <td
                    key={c}
                    title={String(val)}
                    style={{
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        opacity: 0.15,
                        background: getColor(val),
                      }}
                    />
                    <span style={{ position: "relative", zIndex: 1 }}>
                      {val}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KernelMatrix({ data }: { data: number[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="kernel-matrix border-collapse">
        <tbody>
          {data.map((row, r) => (
            <tr key={r}>
              {row.map((val, c) => (
                <td key={c}>{val}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistogramChart({
  before,
  after,
}: {
  before?: number[];
  after?: number[];
}) {
  const width = 512;
  const height = 180;
  const hasBefore = Array.isArray(before) && before.length > 0;
  const hasAfter = Array.isArray(after) && after.length > 0;

  const createPath = (data: number[]) => {
    return data
      .map((v, i) => {
        const safeValue = Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 0;
        const x = (i / Math.max(data.length - 1, 1)) * width;
        const y = height - safeValue * height;

        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  };

  return (
    <div className="space-y-4">
      {hasBefore && (
        <div>
          <p className="text-xs text-muted mb-2">Histogram Sebelum</p>

          <svg
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Histogram sebelum proses"
            className="bg-[#0C1014] rounded-lg border border-border"
            style={{ width: "100%", height: "auto" }}
          >
            <path
              d={createPath(before)}
              fill="none"
              stroke="#60A5FA"
              strokeWidth="1.5"
            />
          </svg>
        </div>
      )}

      {hasAfter && (
        <div>
          <p className="text-xs text-muted mb-2">Histogram Sesudah</p>

          <svg
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Histogram sesudah proses"
            className="bg-[#0C1014] rounded-lg border border-border"
            style={{ width: "100%", height: "auto" }}
          >
            <path
              d={createPath(after)}
              fill="none"
              stroke="#34D399"
              strokeWidth="1.5"
            />
          </svg>
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────

interface ExplanationPanelProps {
  explanation: Explanation | null;
}

export default function ExplanationPanel({
  explanation,
}: ExplanationPanelProps) {
  if (!explanation) {
    return (
      <div className="rounded-xl border border-dashed border-border p-8 text-center text-muted/50">
        <BookOpen size={28} className="mx-auto mb-2 opacity-30" />
        <p className="text-sm">
          Proses gambar untuk melihat penjelasan matematis
        </p>
      </div>
    );
  }

  return (
    <motion.div
      key={explanation.title}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-3"
    >
      {/* Title */}
      <div className="flex items-center gap-3 px-1">
        <div className="flex-shrink-0 w-1 h-8 rounded-full bg-accent" />
        <div>
          <h3
            className="text-lg font-bold text-white"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            {explanation.title}
          </h3>
          <p className="text-xs text-muted mt-0.5">{explanation.description}</p>
        </div>
      </div>

      {/* Image Info */}
      {explanation.image_info && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Object.entries(explanation.image_info).map(([k, v]) => (
            <div
              key={k}
              className="rounded-lg border border-border bg-card px-3 py-2"
            >
              <p className="text-xs text-muted capitalize">
                {k.replace("_", " ")}
              </p>
              <p className="text-sm font-semibold text-accent font-mono">
                {String(v)}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Rumus LaTeX */}
      {explanation.formula && (
        <SectionCard title="Rumus Matematis" icon={BookOpen}>
          <div className="bg-[#0C1014] rounded-lg p-4 text-center overflow-x-auto">
            <BlockMath math={explanation.formula} />
          </div>
        </SectionCard>
      )}

      {/* Kernel */}
      {explanation.kernel && (
        <SectionCard title="Kernel / Mask" icon={Grid}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <KernelMatrix data={explanation.kernel} />
            <div className="text-xs text-muted space-y-1 flex-1">
              <p>
                Kernel ini di-<strong className="text-white">konvolusi</strong>{" "}
                dengan gambar input.
              </p>
              <p>
                Ukuran:{" "}
                <InlineMath
                  math={`${explanation.kernel.length} \\times ${explanation.kernel[0].length}`}
                />
              </p>
              <p>
                Total elemen:{" "}
                <span className="text-accent font-mono">
                  {explanation.kernel.flat().length}
                </span>
              </p>
            </div>
          </div>
        </SectionCard>
      )}

      {/* Pixel Matrices */}
      {(explanation.pixel_before || explanation.pixel_after) && (
        <SectionCard title="Matriks Piksel Sample (Grayscale)" icon={Grid}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {explanation.pixel_before && (
              <PixelMatrix
                data={explanation.pixel_before}
                label="Input (pojok kiri atas)"
              />
            )}
            {explanation.pixel_after && (
              <PixelMatrix
                data={explanation.pixel_after}
                label="Output (setelah proses)"
              />
            )}
          </div>
        </SectionCard>
      )}

      {/* Langkah perhitungan */}
      {explanation.steps && explanation.steps.length > 0 && (
        <SectionCard title="Langkah Perhitungan Manual" icon={Code2}>
          <ol className="space-y-2">
            {explanation.steps.map((step, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3"
              >
                <span className="step-badge">{i + 1}</span>
                <span className="text-sm text-white/80 font-mono leading-relaxed">
                  {step}
                </span>
              </motion.li>
            ))}
          </ol>
        </SectionCard>
      )}

      {/* Pipeline (Studi Kasus) */}
      {explanation.pipeline && (
        <SectionCard title="Pipeline Proses" icon={Cpu}>
          <div className="flex flex-wrap gap-2 items-center">
            {explanation.pipeline.map((stage, i) => (
              <div key={i} className="flex items-center gap-1">
                <div className="rounded-lg border border-accent/40 bg-accent/5 px-3 py-1.5">
                  <p className="text-xs font-semibold text-accent">
                    {stage.name}
                  </p>
                </div>
                {i < explanation.pipeline!.length - 1 && (
                  <span className="text-muted text-xs">→</span>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Affine Matrix */}
      {explanation.matrix && (
        <SectionCard title="Matriks Transformasi Afin" icon={Grid}>
          <div className="bg-[#0C1014] rounded-lg p-4 overflow-x-auto">
            <BlockMath
              math={`M = \\begin{pmatrix} ${explanation.matrix.map((r) => r.map((v) => (typeof v === "number" ? v.toFixed(3) : v)).join(" & ")).join(" \\\\ ")} \\end{pmatrix}`}
            />
          </div>
        </SectionCard>
      )}

      {(explanation.histogram_before || explanation.histogram_after) && (
        <SectionCard title="Histogram Intensitas" icon={BarChart3}>
          <HistogramChart
            before={explanation.histogram_before}
            after={explanation.histogram_after}
          />
        </SectionCard>
      )}
    </motion.div>
  );
}
