// src/pages/Home.tsx
import { motion } from "framer-motion";
import { Layers, Cpu, BookOpen, Zap } from "lucide-react";

const FEATURES = [
  {
    icon: Layers,
    title: "Dasar Pengolahan Citra",
    desc: "Informasi resolusi, mode warna, konversi grayscale dengan visualisasi matriks piksel.",
  },
  {
    icon: Zap,
    title: "Operasi Aritmatika",
    desc: "Blending dua gambar, background subtraction dengan penjelasan matematis step-by-step.",
  },
  {
    icon: Cpu,
    title: "Operasi Spasial",
    desc: "Mean filter, median filter, Sobel edge detection lengkap dengan kernel dan konvolusi manual.",
  },
  {
    icon: BookOpen,
    title: "Studi Kasus",
    desc: "Pipeline lengkap: brightness → contrast → sharpening → denoising untuk foto gelap.",
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
      className="max-w-4xl mx-auto space-y-12"
    >
      {/* Hero */}
      <div className="text-center pt-8 space-y-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5"
        >
          <span className="text-xs text-accent font-medium">
            OpenCV + React + Flask
          </span>
        </motion.div>

        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-4xl md:text-5xl font-bold text-white leading-tight"
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
          className="text-muted text-base max-w-xl mx-auto leading-relaxed"
        >
          Platform edukasi pengolahan citra digital interaktif. Upload gambar,
          pilih operasi, dan lihat penjelasan matematis lengkap secara
          real-time.
        </motion.p>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="flex flex-wrap justify-center gap-3"
        >
          <button
            onClick={() => onNavigate("dasar")}
            className="px-6 py-2.5 bg-accent text-[#0C1014] rounded-xl font-semibold text-sm hover:bg-accent/90 transition-all shadow-glow"
          >
            Mulai Eksplorasi →
          </button>
          <button
            onClick={() => onNavigate("spasial")}
            className="px-6 py-2.5 border border-border bg-card text-white rounded-xl font-semibold text-sm hover:border-accent/50 transition-all"
          >
            Operasi Spasial
          </button>
        </motion.div>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FEATURES.map((feat, i) => {
          const Icon = feat.icon;
          return (
            <motion.div
              key={feat.title}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 * (i + 3) }}
              className="rounded-xl border border-border bg-card p-5 hover:border-accent/30 transition-all group"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-accent/10 border border-accent/20 group-hover:bg-accent/15 transition-colors">
                  <Icon size={18} className="text-accent" />
                </div>
                <div>
                  <h3 className="font-semibold text-white text-sm mb-1">
                    {feat.title}
                  </h3>
                  <p className="text-xs text-muted leading-relaxed">
                    {feat.desc}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Tech badges */}
      <div className="flex flex-wrap justify-center gap-2 pb-4">
        {[
          "Python 3.11",
          "OpenCV 4.x",
          "Flask 3.x",
          "React 18",
          "TypeScript",
          "NumPy",
          "Tailwind CSS",
        ].map((tech) => (
          <span
            key={tech}
            className="px-3 py-1 text-xs font-mono border border-border bg-card text-muted rounded-full"
          >
            {tech}
          </span>
        ))}
      </div>
    </motion.div>
  );
}
