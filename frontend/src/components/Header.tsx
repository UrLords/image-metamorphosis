import { Layers, LogOut, Menu, UserCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface HeaderProps {
  onNavigate: (page: string) => void;
  onToggleSidebar: () => void;
}

export default function Header({ onNavigate, onToggleSidebar }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header
      className="fixed left-0 right-0 top-0 z-50 flex h-14 items-center justify-between px-4"
      style={{
        backgroundColor: "#DFD0B8",
        boxShadow: "0 2px 12px rgba(0,0,0,0.35)",
      }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="rounded p-1.5 transition-colors hover:bg-black/10"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} className="text-black" />
        </button>
        <button
          className="flex items-center gap-1.5"
          onClick={() => onNavigate("home")}
        >
          <Layers size={18} className="text-black" />
          <span
            className="hidden text-sm font-semibold tracking-wide text-black sm:block"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            IM
          </span>
        </button>
      </div>

      <h1
        className="absolute left-1/2 -translate-x-1/2 text-lg font-bold tracking-tight text-black md:text-xl"
        style={{ fontFamily: "'Playfair Display', serif" }}
      >
        Image Metamorphosis
      </h1>

      <div className="flex items-center gap-2">
        {user?.photoURL ? (
          <img
            src={user.photoURL}
            alt="User"
            className="h-7 w-7 rounded-full border border-black/20"
          />
        ) : (
          <UserCircle size={24} className="text-black/70" />
        )}
        <span className="hidden max-w-36 truncate text-xs font-medium text-black/75 sm:block">
          {user?.displayName || user?.email}
        </span>
        <button
          type="button"
          onClick={logout}
          className="rounded p-1.5 text-black/70 transition hover:bg-black/10 hover:text-black"
          title="Logout"
          aria-label="Logout"
        >
          <LogOut size={17} />
        </button>
      </div>
    </header>
  );
}
