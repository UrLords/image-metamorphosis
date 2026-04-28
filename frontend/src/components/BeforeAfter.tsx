// src/components/BeforeAfter.tsx
import { motion } from "framer-motion";
import { ArrowRight, ImageOff } from "lucide-react";

interface BeforeAfterProps {
  before: string | null;
  after: string | null;
  isLoading: boolean;
}

export default function BeforeAfter({
  before,
  after,
  isLoading,
}: BeforeAfterProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
      {/* ── Before ── */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-muted"></div>
          <span className="text-xs font-medium text-muted uppercase tracking-widest">
            Sebelum
          </span>
        </div>
        <div className="rounded-xl border border-border bg-card overflow-hidden min-h-48 flex items-center justify-center">
          {before ? (
            <img
              src={before}
              alt="Before"
              className="w-full object-contain max-h-72"
            />
          ) : (
            <div className="flex flex-col items-center gap-2 text-muted py-12">
              <ImageOff size={32} className="opacity-40" />
              <span className="text-xs">Belum ada gambar</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Arrow (hidden on mobile) ── */}
      <div className="hidden md:flex items-center justify-center absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
        <ArrowRight size={20} className="text-accent opacity-60" />
      </div>

      {/* ── After ── */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent"></div>
          <span className="text-xs font-medium text-accent uppercase tracking-widest">
            Sesudah
          </span>
        </div>
        <div className="rounded-xl border border-accent/30 bg-card overflow-hidden min-h-48 flex items-center justify-center relative">
          {isLoading ? (
            <motion.div
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex flex-col items-center gap-3 py-12"
            >
              {/* Spinner */}
              <div className="relative w-12 h-12">
                <div className="absolute inset-0 rounded-full border-2 border-accent/20"></div>
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
              </div>
              <span className="text-xs text-accent">Memproses...</span>
            </motion.div>
          ) : after ? (
            <motion.img
              key={after}
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35 }}
              src={after}
              alt="After"
              className="w-full object-contain max-h-72"
            />
          ) : (
            <div className="flex flex-col items-center gap-2 text-muted/50 py-12">
              <div className="w-10 h-10 rounded-full border border-dashed border-muted/30 flex items-center justify-center">
                <span className="text-lg text-muted/30">?</span>
              </div>
              <span className="text-xs">Hasil akan muncul di sini</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
