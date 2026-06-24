import { motion } from "framer-motion";
import { AlertCircle, Layers, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { signInWithGoogle, loading, error } = useAuth();

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{
        backgroundColor: "#0C1014",
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card"
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-accent/30 bg-accent/10">
            <Layers size={30} className="text-accent" />
          </div>
          <div>
            <h1
              className="text-2xl font-bold text-white"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              Image Metamorphosis
            </h1>
            <p className="mt-1 text-xs text-muted">
              Masuk untuk memakai fitur pengolahan citra.
            </p>
          </div>
        </div>

        <div className="my-6 border-t border-border" />

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/15 p-3 text-sm text-red-200">
            <AlertCircle size={15} />
            {error}
          </div>
        )}

        <button
          type="button"
          onClick={signInWithGoogle}
          disabled={loading}
          className="flex w-full items-center justify-center gap-3 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-900 transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
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
          )}
          {loading ? "Memuat..." : "Masuk dengan Google"}
        </button>

        <div className="mt-5 rounded-xl border border-border bg-[#0C1014] p-3 text-xs leading-relaxed text-muted">
          Google Sign-In dipakai untuk mengamankan fitur, menyimpan riwayat
          proses, dan menghubungkan hasil scan ke akun kamu.
        </div>
      </motion.div>
    </div>
  );
}
