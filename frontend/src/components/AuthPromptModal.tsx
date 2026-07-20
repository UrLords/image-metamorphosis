import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, LockKeyhole, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"
      />
      <path
        fill="#34A853"
        d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"
      />
      <path
        fill="#FBBC05"
        d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18z"
      />
      <path
        fill="#EA4335"
        d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"
      />
    </svg>
  );
}

export default function AuthPromptModal() {
  const {
    error,
    isLoginPromptOpen,
    signInWithGoogle,
    closeLoginPrompt,
  } = useAuth();

  useEffect(() => {
    if (!isLoginPromptOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeLoginPrompt();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isLoginPromptOpen, closeLoginPrompt]);

  return (
    <AnimatePresence>
      {isLoginPromptOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 px-4 backdrop-blur-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeLoginPrompt();
          }}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="auth-prompt-title"
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 340, damping: 28 }}
            className="relative w-full max-w-md overflow-hidden rounded-xl border border-white/10 bg-[#11171D] p-6 shadow-[0_28px_90px_rgba(0,0,0,0.62)] sm:p-7"
          >
            <button
              type="button"
              onClick={closeLoginPrompt}
              className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.035] text-white/55 transition hover:bg-white/[0.08] hover:text-white"
              aria-label="Tutup dialog login"
            >
              <X size={17} />
            </button>

            <div className="flex items-start gap-4 pr-10">
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl border border-accent/30 bg-accent/10 text-accent">
                <LockKeyhole size={22} />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-accent">
                  Satu langkah lagi
                </p>
                <h2
                  id="auth-prompt-title"
                  className="mt-1 text-xl font-bold text-white"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  Masuk untuk memproses gambar
                </h2>
              </div>
            </div>

            <p className="mt-5 text-sm leading-relaxed text-white/60">
              Kamu bebas menjelajahi materi dan menyiapkan gambar. Login hanya
              diperlukan saat ImageMeta mulai memproses atau mengekspor hasil.
            </p>

            {error && (
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
                <AlertCircle size={15} className="flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="button"
              onClick={signInWithGoogle}
              className="mt-6 flex w-full items-center justify-center gap-3 rounded-lg bg-white px-4 py-3 text-sm font-semibold text-slate-900 transition hover:bg-white/90"
            >
              <GoogleIcon />
              Lanjutkan dengan Google
            </button>

            <p className="mt-3 text-center text-[11px] leading-relaxed text-white/38">
              Akun digunakan untuk keamanan proses dan menghubungkan riwayat
              hasil ke profil kamu.
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
