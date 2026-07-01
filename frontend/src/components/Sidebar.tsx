import { motion, AnimatePresence } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Aperture,
  Ban,
  Binary,
  Blend,
  ChevronDown,
  ChevronRight,
  CircleSlash,
  Contrast,
  Divide,
  Droplets,
  Expand,
  FileScan,
  Filter,
  FlipHorizontal2,
  ImageIcon,
  Maximize2,
  Microscope,
  Minimize2,
  Minus,
  Move,
  Palette,
  Plus,
  RotateCw,
  ScanLine,
  ScanText,
  Shapes,
  Sigma,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Wand2,
} from "lucide-react";
import { useMemo, useState } from "react";

interface MenuItem {
  id: string;
  label: string;
  icon: LucideIcon;
}

interface MenuGroup {
  section: string;
  icon: LucideIcon;
  accent: string;
  items: MenuItem[];
}

const MENU: MenuGroup[] = [
  {
    section: "Dasar Citra",
    icon: ImageIcon,
    accent: "#C9A86C",
    items: [{ id: "grayscale", label: "Konversi Grayscale", icon: ImageIcon }],
  },
  {
    section: "Operasi Aritmatika",
    icon: Sigma,
    accent: "#D4B77D",
    items: [
      { id: "blending", label: "Image Blending", icon: Blend },
      { id: "subtraction", label: "Background Subtraction", icon: Minus },
      { id: "multiply", label: "Image Multiplication", icon: Plus },
      { id: "divide", label: "Image Division", icon: Divide },
    ],
  },
  {
    section: "Geometri",
    icon: Shapes,
    accent: "#B7D0B1",
    items: [
      { id: "rotation", label: "Rotasi", icon: RotateCw },
      { id: "scaling", label: "Scaling", icon: Expand },
      { id: "translation", label: "Translasi", icon: Move },
      { id: "flip", label: "Flip", icon: FlipHorizontal2 },
    ],
  },
  {
    section: "Operasi Titik",
    icon: SlidersHorizontal,
    accent: "#D7A46D",
    items: [
      { id: "brightness", label: "Brightness", icon: Sun },
      { id: "contrast", label: "Contrast", icon: Contrast },
      { id: "negative", label: "Negative", icon: CircleSlash },
      { id: "saturation", label: "Saturation", icon: Droplets },
      { id: "hue_shift", label: "Hue Shift", icon: Palette },
      { id: "opacity", label: "Opacity", icon: Aperture },
      { id: "sharpness", label: "Sharpness", icon: Sparkles },
    ],
  },
  {
    section: "Operasi Spasial",
    icon: Filter,
    accent: "#9EB8D9",
    items: [
      { id: "mean_filter", label: "Mean Filter", icon: Minimize2 },
      { id: "gaussian_blur", label: "Gaussian Blur", icon: Activity },
      { id: "median_filter", label: "Median Filter", icon: Maximize2 },
    ],
  },
  {
    section: "Morfologi Citra",
    icon: Microscope,
    accent: "#C7B3E5",
    items: [
      { id: "morphology", label: "Morphology", icon: Shapes },
      { id: "zhang_suen", label: "Thinning Zhang-Suen", icon: Binary },
    ],
  },
  {
    section: "Deteksi Tepi",
    icon: Activity,
    accent: "#8FC8BC",
    items: [
      { id: "sobel", label: "Sobel Edge Detection", icon: Activity },
      { id: "edge_detection", label: "Edge Detection", icon: ScanLine },
    ],
  },
  {
    section: "Segmentasi Citra",
    icon: Aperture,
    accent: "#E5BE8B",
    items: [{ id: "segmentation", label: "Segmentasi Citra", icon: Ban }],
  },
  {
    section: "Scan Dokumen",
    icon: FileScan,
    accent: "#D3BA75",
    items: [{ id: "scan_document", label: "Scan & Restore", icon: ScanText }],
  },
  {
    section: "Advanced Editor",
    icon: Wand2,
    accent: "#D8A1A1",
    items: [{ id: "advanced_editor", label: "Photo Editor", icon: Wand2 }],
  },
];

interface SidebarProps {
  isOpen: boolean;
  activeOperation: string;
  onSelectOperation: (opId: string) => void;
}

export default function Sidebar({
  isOpen,
  activeOperation,
  onSelectOperation,
}: SidebarProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries(MENU.map((m) => [m.section, true])),
  );

  const activeGroup = useMemo(
    () => MENU.find((group) => group.items.some((item) => item.id === activeOperation)),
    [activeOperation],
  );

  const toggle = (section: string) =>
    setExpanded((prev) => ({ ...prev, [section]: !prev[section] }));

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          key="sidebar"
          initial={{ x: -320, opacity: 0, scale: 0.98 }}
          animate={{ x: 0, opacity: 1, scale: 1 }}
          exit={{ x: -320, opacity: 0, scale: 0.98 }}
          transition={{ type: "spring", stiffness: 260, damping: 28 }}
          className="fixed bottom-4 left-4 top-20 z-40 flex w-72 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0B0F12]/95 shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        >
          <div className="border-b border-white/10 px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#C9A86C]/35 bg-[#C9A86C]/10 p-1.5 shadow-[0_12px_35px_rgba(201,168,108,0.12)]">
                <img src="/imagemeta-mark.png" alt="" className="h-full w-full object-contain" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">ImageMeta</p>
                <p className="truncate text-[11px] text-white/45">
                  {activeGroup?.section ?? "Workspace"}
                </p>
              </div>
            </div>
          </div>

          <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-3 [scrollbar-width:thin] [scrollbar-color:#3B3327_transparent]">
            {MENU.map((group) => {
              const Icon = group.icon;
              const isExpanded = expanded[group.section];
              const groupActive = group.items.some((item) => item.id === activeOperation);

              return (
                <div key={group.section} className="rounded-xl">
                  <button
                    type="button"
                    onClick={() => toggle(group.section)}
                    className={`group flex w-full items-center justify-between rounded-xl px-2.5 py-2 transition-all duration-200 ${
                      groupActive
                        ? "bg-white/[0.07] text-white"
                        : "text-white/62 hover:bg-white/[0.045] hover:text-white"
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-2.5">
                      <span
                        className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border transition-transform duration-200 group-hover:scale-105"
                        style={{
                          borderColor: `${group.accent}45`,
                          backgroundColor: groupActive ? `${group.accent}22` : "rgba(255,255,255,0.035)",
                          color: groupActive ? group.accent : "rgba(255,255,255,0.64)",
                        }}
                      >
                        <Icon size={16} strokeWidth={2.1} />
                      </span>
                      <span className="truncate text-left text-[11px] font-semibold uppercase tracking-[0.12em]">
                        {group.section}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-white/38">
                        {group.items.length}
                      </span>
                      {isExpanded ? (
                        <ChevronDown size={14} className="text-white/45" />
                      ) : (
                        <ChevronRight size={14} className="text-white/45" />
                      )}
                    </div>
                  </button>

                  <AnimatePresence initial={false}>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18, ease: "easeOut" }}
                        className="overflow-hidden"
                      >
                        <div className="space-y-1 py-1.5 pl-3">
                          {group.items.map((item) => {
                            const ItemIcon = item.icon;
                            const isActive = activeOperation === item.id;
                            return (
                              <motion.button
                                key={item.id}
                                type="button"
                                onClick={() => onSelectOperation(item.id)}
                                whileHover={{ x: 3 }}
                                transition={{ duration: 0.16 }}
                                className={`relative flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-sm transition-all duration-200 ${
                                  isActive
                                    ? "bg-[#DFD0B8] font-semibold text-[#111417] shadow-[0_12px_30px_rgba(201,168,108,0.22)]"
                                    : "text-white/62 hover:bg-white/[0.055] hover:text-white"
                                }`}
                              >
                                {isActive && (
                                  <motion.span
                                    layoutId="sidebar-active-pill"
                                    className="absolute inset-0 rounded-xl border border-[#F0DCA8]/30"
                                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                                  />
                                )}
                                <span
                                  className={`relative flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg ${
                                    isActive ? "bg-[#111417]/10" : "bg-white/[0.04]"
                                  }`}
                                >
                                  <ItemIcon size={14} strokeWidth={2.15} />
                                </span>
                                <span className="relative min-w-0 truncate">{item.label}</span>
                              </motion.button>
                            );
                          })}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </nav>

          <div className="border-t border-white/10 p-3">
            <div className="rounded-xl border border-[#C9A86C]/20 bg-[#C9A86C]/8 px-3 py-2">
              <p className="text-[11px] font-medium text-[#EAD7AB]">ImageMeta v1</p>
              <p className="mt-0.5 text-[10px] text-white/42">Learning workspace</p>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
