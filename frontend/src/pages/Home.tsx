import { motion } from "framer-motion";
import { Cpu, Layers, ScanLine, Wand2, Zap, Filter, Dot } from "lucide-react";

const FEATURES = [
  {
    icon: Layers,
    title: "Dasar Pengolahan Citra",
    desc: "Informasi resolusi, mode warna, konversi grayscale, dan visualisasi matriks piksel.",
  },
  {
    icon: Zap,
    title: "Operasi Aritmatika",
    desc: "Blending dua gambar, background subtraction, multiplication, dan division dengan penjelasan matematis.",
  },
  {
    icon: Cpu,
    title: "Operasi Spasial",
    desc: "Mean filter, Gaussian blur, dan median filter lengkap dengan kernel dan penjelasan matematis.",
  },
  {
    icon: Layers,
    title: "Morfologi Citra",
    desc: "Dilasi, erosi, opening, closing, boundary extraction, dan thinning Zhang-Suen.",
  },
  {
    icon: Filter,
    title: "Deteksi Tepi",
    desc: "Sobel, Canny, Prewitt, Roberts, dan Laplacian untuk memahami batas antar region.",
  },
  {
    icon: Dot,
    title: "Segmentasi Citra",
    desc: "Global thresholding, adaptive thresholding, Otsu, dan K-Means color segmentation.",
  },
  {
    icon: ScanLine,
    title: "Scan Dokumen",
    desc: "Deteksi kertas, deskew perspektif, peningkatan teks, dan output hitam-putih, grayscale, atau warna.",
  },
  {
    icon: Wand2,
    title: "Advanced Editor",
    desc: "Editor foto lengkap: preview real-time, crop, filter, rotasi, flip, dan export PNG/JPG.",
  },
];

interface HomeProps {
  onNavigate: (page: string) => void;
}

export default function Home({ onNavigate }: HomeProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="mx-auto max-w-4xl space-y-12"
    >
      <div className="space-y-4 pt-8 text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5"
        >
          <span className="text-xs font-medium text-accent">
            OpenCV + React + Flask
          </span>
        </motion.div>

        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-4xl font-bold leading-tight text-white md:text-5xl"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Image
          <br />
          <span className="text-accent">Metamorphosis</span>
        </motion.h1>

        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mx-auto max-w-xl text-base leading-relaxed text-muted"
        >
          Platform edukasi pengolahan citra digital interaktif. Upload gambar,
          pilih operasi, scan dokumen, edit foto, dan lihat penjelasan matematis
          secara real-time.
        </motion.p>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="flex flex-wrap justify-center gap-3"
        >
          <button
            onClick={() => onNavigate("dasar")}
            className="rounded-xl bg-accent px-6 py-2.5 text-sm font-semibold text-[#0C1014] shadow-glow transition-all hover:bg-accent/90"
          >
            Mulai Eksplorasi
          </button>
          <button
            onClick={() => onNavigate("scan")}
            className="rounded-xl border border-accent/40 bg-accent/10 px-6 py-2.5 text-sm font-semibold text-accent transition-all hover:bg-accent/20"
          >
            Scan Dokumen
          </button>
          <button
            onClick={() => onNavigate("editor")}
            className="rounded-xl border border-border bg-card px-6 py-2.5 text-sm font-semibold text-white transition-all hover:border-accent/50"
          >
            Buka Editor
          </button>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {FEATURES.map((feat, i) => {
          const Icon = feat.icon;
          return (
            <motion.div
              key={feat.title}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 * (i + 3) }}
              className="group rounded-xl border border-border bg-card p-5 transition-all hover:border-accent/30"
            >
              <div className="flex items-start gap-3">
                <div className="rounded-lg border border-accent/20 bg-accent/10 p-2 transition-colors group-hover:bg-accent/15">
                  <Icon size={18} className="text-accent" />
                </div>
                <div>
                  <h3 className="mb-1 text-sm font-semibold text-white">
                    {feat.title}
                  </h3>
                  <p className="text-xs leading-relaxed text-muted">
                    {feat.desc}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
