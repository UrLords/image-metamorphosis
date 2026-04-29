// src/components/Header.tsx
import { Menu, Layers } from "lucide-react";

interface NavItem {
  id: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "home", label: "Home" },
  { id: "dasar", label: "Dasar Citra" },
  { id: "aritmatika", label: "Aritmatika" },
  { id: "geometri", label: "Geometri" },
  { id: "titik", label: "Op. Titik" },
  { id: "spasial", label: "Op. Spasial" },
  { id: "studi", label: "Studi Kasus" },
];

interface HeaderProps {
  activePage: string;
  onNavigate: (page: string) => void;
  onToggleSidebar: () => void;
}

export default function Header({
  activePage,
  onNavigate,
  onToggleSidebar,
}: HeaderProps) {
  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 h-14"
      style={{
        backgroundColor: "#DFD0B8",
        boxShadow: "0 2px 12px rgba(0,0,0,0.35)",
      }}
    >
      {/* ── Kiri: Hamburger + Logo ── */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded hover:bg-black/10 transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} className="text-black" />
        </button>
        <div className="flex items-center gap-1.5">
          <Layers size={18} className="text-black" />
          <span
            className="text-black font-semibold text-sm tracking-wide hidden sm:block"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            IM
          </span>
        </div>
      </div>

      {/* ── Tengah: Judul ── */}
      <h1
        className="absolute left-1/2 -translate-x-1/2 text-black font-bold text-lg md:text-xl tracking-tight"
        style={{
          fontFamily: "'Playfair Display', serif",
          letterSpacing: "-0.01em",
        }}
      >
        Image Metamorphosis
      </h1>

      {/* ── Kanan: Nav ── */}
      {/* <nav className="hidden lg:flex items-center gap-0.5">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`
              px-3 py-1.5 rounded text-sm font-medium transition-all
              ${
                activePage === item.id
                  ? "bg-black/15 text-black"
                  : "text-black/70 hover:text-black hover:bg-black/10"
              }
            `}
          >
            {item.label}
          </button>
        ))}
      </nav> */}
    </header>
  );
}
