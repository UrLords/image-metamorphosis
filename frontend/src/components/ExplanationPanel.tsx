import { useState } from "react";
import type React from "react";
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
import type {
  Explanation,
  HistogramData,
  HistogramPayload,
} from "../api/imageApi";

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
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 transition-colors hover:bg-white/5"
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
  const getColor = (value: number) => {
    const intensity = Math.round(value);
    return `rgb(${intensity},${intensity},${intensity})`;
  };

  return (
    <div>
      {label && <p className="mb-2 text-xs text-muted">{label}</p>}
      <div className="overflow-x-auto">
        <table className="pixel-matrix border-collapse">
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((value, columnIndex) => (
                  <td
                    key={columnIndex}
                    title={String(value)}
                    style={{ position: "relative" }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        opacity: 0.15,
                        background: getColor(value),
                      }}
                    />
                    <span style={{ position: "relative", zIndex: 1 }}>
                      {value}
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
          {data.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, columnIndex) => (
                <td key={columnIndex}>{value}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type ChannelKey = "red" | "green" | "blue" | "luminance";

const CHANNELS: Array<{
  key: ChannelKey;
  label: string;
  color: string;
  hint: string;
}> = [
  { key: "red", label: "Red", color: "#FF5A6A", hint: "Komponen merah" },
  { key: "green", label: "Green", color: "#57D68D", hint: "Komponen hijau" },
  { key: "blue", label: "Blue", color: "#5BA7FF", hint: "Komponen biru" },
  {
    key: "luminance",
    label: "Luminance",
    color: "#E6E8EC",
    hint: "Terang-gelap",
  },
];

function emptyHistogramData(): HistogramData {
  return { red: [], green: [], blue: [], luminance: [] };
}

function normalizeHistogram(payload?: HistogramPayload): HistogramData | null {
  if (!payload) return null;
  if (Array.isArray(payload)) {
    return { red: [], green: [], blue: [], luminance: payload };
  }
  return { ...emptyHistogramData(), ...payload };
}

function hasHistogramData(data: HistogramData | null) {
  return Boolean(data && CHANNELS.some((channel) => data[channel.key]?.length));
}

function histogramLine(data: number[], width: number, height: number) {
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

function CombinedHistogram({
  title,
  data,
}: {
  title: string;
  data: HistogramData;
}) {
  const width = 720;
  const height = 260;
  const activeChannels = CHANNELS.filter(
    (channel) => data[channel.key]?.length,
  );

  return (
    <div className="rounded-xl border border-border bg-[#0C1014] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-white">{title}</h4>
          <p className="text-[10px] text-muted">
            Semua channel digabung dalam satu bidang.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {activeChannels.map((channel) => (
            <span
              key={channel.key}
              className="flex items-center gap-1.5 text-[10px] text-muted"
            >
              <span
                className="h-2.5 w-2.5 rounded-sm"
                style={{ background: channel.color }}
              />
              {channel.label}
            </span>
          ))}
        </div>
      </div>

      {activeChannels.length ? (
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="block h-auto min-h-[220px] w-full rounded-lg border border-border bg-[#090D11]"
        >
          {[0.25, 0.5, 0.75].map((ratio) => (
            <line
              key={ratio}
              x1="0"
              x2={width}
              y1={height * ratio}
              y2={height * ratio}
              stroke="#2A3340"
              strokeOpacity="0.55"
              strokeWidth="1"
            />
          ))}
          <line
            x1="0"
            x2={width}
            y1={height - 1}
            y2={height - 1}
            stroke="#2A3340"
            strokeWidth="1"
          />
          <line
            x1={width / 2}
            x2={width / 2}
            y1="0"
            y2={height}
            stroke="#2A3340"
            strokeOpacity="0.7"
            strokeWidth="1"
          />
          {activeChannels.map((channel) => (
            <path
              key={channel.key}
              d={histogramLine(data[channel.key] ?? [], width, height)}
              fill="none"
              stroke={channel.color}
              strokeWidth={channel.key === "luminance" ? 2.4 : 1.8}
              strokeOpacity={channel.key === "luminance" ? 0.95 : 0.78}
            />
          ))}
        </svg>
      ) : (
        <div className="flex h-[170px] items-center justify-center rounded border border-dashed border-border text-[10px] text-muted/60">
          Tidak tersedia
        </div>
      )}

      <div className="mt-2 flex justify-between font-mono text-[10px] text-muted/60">
        <span>0 gelap</span>
        <span>128 mid</span>
        <span>255 terang</span>
      </div>
    </div>
  );
}

export function HistogramChart({
  before,
  after,
}: {
  before?: HistogramPayload;
  after?: HistogramPayload;
}) {
  const beforeData = normalizeHistogram(before);
  const afterData = normalizeHistogram(after);

  if (!hasHistogramData(beforeData) && !hasHistogramData(afterData))
    return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-5 2xl:grid-cols-2">
        {beforeData && hasHistogramData(beforeData) && (
          <CombinedHistogram title="Sebelum" data={beforeData} />
        )}
        {afterData && hasHistogramData(afterData) && (
          <CombinedHistogram title="Sesudah" data={afterData} />
        )}
      </div>

      <div className="rounded-lg border border-border bg-[#0C1014] p-3 text-[11px] leading-relaxed text-muted">
        <p className="font-semibold text-white">Cara membaca histogram:</p>
        <p>
          Semua channel ditumpuk dalam satu chart agar mudah dibandingkan. Garis
          merah, hijau, dan biru menunjukkan distribusi warna; garis putih
          menunjukkan luminance atau terang-gelap.
        </p>
      </div>
    </div>
  );
}

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
      <div className="flex items-center gap-3 px-1">
        <div className="h-8 w-1 flex-shrink-0 rounded-full bg-accent" />
        <div>
          <h3
            className="text-lg font-bold text-white"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            {explanation.title}
          </h3>
          <p className="mt-0.5 text-xs text-muted">{explanation.description}</p>
        </div>
      </div>

      {explanation.image_info && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Object.entries(explanation.image_info).map(([key, value]) => (
            <div
              key={key}
              className="rounded-lg border border-border bg-card px-3 py-2"
            >
              <p className="text-xs capitalize text-muted">
                {key.replace("_", " ")}
              </p>
              <p className="font-mono text-sm font-semibold text-accent">
                {String(value)}
              </p>
            </div>
          ))}
        </div>
      )}

      {explanation.formula && (
        <SectionCard title="Rumus Matematis" icon={BookOpen}>
          <div className="overflow-x-auto rounded-lg bg-[#0C1014] p-4 text-center">
            <BlockMath math={explanation.formula} />
          </div>
        </SectionCard>
      )}

      {explanation.kernel && (
        <SectionCard title="Kernel / Mask" icon={Grid}>
          <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <KernelMatrix data={explanation.kernel} />
            <div className="flex-1 space-y-1 text-xs text-muted">
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
                <span className="font-mono text-accent">
                  {explanation.kernel.flat().length}
                </span>
              </p>
            </div>
          </div>
        </SectionCard>
      )}

      {(explanation.pixel_before || explanation.pixel_after) && (
        <SectionCard title="Matriks Piksel Sample (Grayscale)" icon={Grid}>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
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

      {explanation.steps && explanation.steps.length > 0 && (
        <SectionCard title="Langkah Perhitungan Manual" icon={Code2}>
          <ol className="space-y-2">
            {explanation.steps.map((step, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-start gap-3"
              >
                <span className="step-badge">{index + 1}</span>
                <span className="font-mono text-sm leading-relaxed text-white/80">
                  {step}
                </span>
              </motion.li>
            ))}
          </ol>
        </SectionCard>
      )}

      {explanation.pipeline && (
        <SectionCard title="Pipeline Proses" icon={Cpu}>
          <div className="flex flex-wrap items-center gap-2">
            {explanation.pipeline.map((stage, index) => (
              <div key={index} className="flex items-center gap-1">
                <div className="rounded-lg border border-accent/40 bg-accent/5 px-3 py-1.5">
                  <p className="text-xs font-semibold text-accent">
                    {stage.name}
                  </p>
                </div>
                {index < explanation.pipeline!.length - 1 && (
                  <span className="text-xs text-muted">-&gt;</span>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {explanation.matrix && (
        <SectionCard title="Matriks Transformasi Afin" icon={Grid}>
          <div className="overflow-x-auto rounded-lg bg-[#0C1014] p-4">
            <BlockMath
              math={`M = \\begin{pmatrix} ${explanation.matrix
                .map((row) =>
                  row
                    .map((value) =>
                      typeof value === "number" ? value.toFixed(3) : value,
                    )
                    .join(" & "),
                )
                .join(" \\\\ ")} \\end{pmatrix}`}
            />
          </div>
        </SectionCard>
      )}

      {(explanation.histogram_before || explanation.histogram_after) && (
        <SectionCard title="Histogram RGB dan Luminance" icon={BarChart3}>
          <HistogramChart
            before={explanation.histogram_before}
            after={explanation.histogram_after}
          />
        </SectionCard>
      )}
    </motion.div>
  );
}
