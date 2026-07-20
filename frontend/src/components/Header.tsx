import { LogIn, LogOut, Menu, UserCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface HeaderProps {
  onNavigate: (page: string) => void;
  onToggleSidebar: () => void;
}

export default function Header({ onNavigate, onToggleSidebar }: HeaderProps) {
  const { user, loading, logout, openLoginPrompt } = useAuth();

  return (
    <header className="fixed left-0 right-0 top-0 z-50 flex h-16 items-center justify-between border-b border-white/10 bg-[#080C10]/90 px-4 shadow-[0_14px_50px_rgba(0,0,0,0.36)] backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] text-white/70 transition-all hover:border-[#C9A86C]/40 hover:bg-[#C9A86C]/10 hover:text-[#EAD7AB]"
          aria-label="Toggle sidebar"
        >
          <Menu size={19} />
        </button>
        <button
          className="flex items-center gap-2.5 rounded-xl px-2 py-1.5 transition-colors hover:bg-white/[0.045]"
          onClick={() => onNavigate("home")}
          aria-label="Image Metamorphosis home"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#C9A86C]/25 bg-[#C9A86C]/10 p-1.5">
            <img
              src="/imagemeta-mark.png"
              alt=""
              className="h-full w-full object-contain drop-shadow-[0_1px_2px_rgba(0,0,0,0.35)]"
              aria-hidden="true"
            />
          </span>
          <span className="hidden text-sm font-semibold tracking-wide text-white sm:block">
            ImageMeta
          </span>
        </button>
      </div>

      <div className="flex items-center gap-2.5">
        {user ? (
          <>
            <div className="hidden items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] py-1.5 pl-2 pr-3 sm:flex">
              {user.photoURL ? (
                <img
                  src={user.photoURL}
                  alt="Foto profil"
                  className="h-7 w-7 rounded-lg border border-[#C9A86C]/30 object-cover"
                />
              ) : (
                <UserCircle size={24} className="text-white/55" />
              )}
              <span className="max-w-40 truncate text-xs font-medium text-white/72">
                {user.displayName || user.email}
              </span>
            </div>
            <button
              type="button"
              onClick={logout}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] text-white/62 transition-all hover:border-red-300/30 hover:bg-red-500/10 hover:text-red-100"
              title="Keluar"
              aria-label="Keluar"
            >
              <LogOut size={17} />
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={openLoginPrompt}
            disabled={loading}
            className="flex h-10 items-center justify-center gap-2 rounded-xl border border-accent/35 bg-accent/10 px-3.5 text-xs font-semibold text-accent transition-all hover:border-accent/60 hover:bg-accent/15 disabled:cursor-wait disabled:opacity-50"
          >
            <LogIn size={16} />
            {loading ? "Memuat" : "Masuk"}
          </button>
        )}
      </div>
    </header>
  );
}
