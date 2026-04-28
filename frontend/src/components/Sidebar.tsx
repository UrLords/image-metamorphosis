// src/components/Sidebar.tsx
import { motion, AnimatePresence } from "framer-motion";
import {
  ImageIcon,
  Plus,
  RotateCw,
  Dot,
  Filter,
  BookOpen,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";

// ── Data Sidebar ──────────────────────────────────────────────
const MENU = [
  {
    section: "Dasar Citra",
    icon: ImageIcon,
    page: "dasar",
    items: [{ id: "grayscale", label: "Konversi Grayscale" }],
  },
  {
    section: "Operasi Aritmatika",
    icon: Plus,
    page: "aritmatika",
    items: [
      { id: "blending", label: "Image Blending" },
      { id: "subtraction", label: "Background Subtraction" },
    ],
  },
  {
    section: "Geometri",
    icon: RotateCw,
    page: "geometri",
    items: [
      { id: "rotation", label: "Rotasi" },
      { id: "scaling", label: "Scaling" },
      { id: "translation", label: "Translasi" },
      { id: "flip", label: "Flip" },
    ],
  },
  {
    section: "Operasi Titik",
    icon: Dot,
    page: "titik",
    items: [
      { id: "brightness", label: "Brightness" },
      { id: "contrast", label: "Contrast" },
      { id: "negative", label: "Negative" },
      { id: "thresholding", label: "Thresholding" },
    ],
  },
  {
    section: "Operasi Spasial",
    icon: Filter,
    page: "spasial",
    items: [
      { id: "mean_filter", label: "Mean Filter" },
      { id: "median_filter", label: "Median Filter" },
      { id: "sobel", label: "Sobel Edge Detection" },
    ],
  },
  {
    section: "Studi Kasus",
    icon: BookOpen,
    page: "studi",
    items: [{ id: "enhance_pipeline", label: "Enhancement Pipeline" }],
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
  // Track which section is expanded
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries(MENU.map((m) => [m.section, true])),
  );

  const toggle = (section: string) =>
    setExpanded((prev) => ({ ...prev, [section]: !prev[section] }));

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          key="sidebar"
          initial={{ x: -280, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -280, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed left-0 top-14 bottom-0 z-40 w-64 overflow-y-auto py-4 flex flex-col"
          style={{
            backgroundColor: "#948979",
            boxShadow: "4px 0 24px rgba(0,0,0,0.4)",
          }}
        >
          {MENU.map((group) => {
            const Icon = group.icon;
            const isExpanded = expanded[group.section];

            return (
              <div key={group.section} className="mb-1">
                {/* Section header */}
                <button
                  onClick={() => toggle(group.section)}
                  className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-black/10 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon size={15} className="text-black/70 flex-shrink-0" />
                    <span
                      className="text-black font-semibold text-xs uppercase tracking-wider"
                      style={{ fontFamily: "'DM Sans', sans-serif" }}
                    >
                      {group.section}
                    </span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown size={14} className="text-black/60" />
                  ) : (
                    <ChevronRight size={14} className="text-black/60" />
                  )}
                </button>

                {/* Items */}
                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      {group.items.map((item) => {
                        const isActive = activeOperation === item.id;
                        return (
                          <button
                            key={item.id}
                            onClick={() => onSelectOperation(item.id)}
                            className={`
                              w-full text-left pl-10 pr-4 py-2 text-sm transition-all
                              ${
                                isActive
                                  ? "bg-[#0C1014] text-[#C9A86C] font-medium border-r-2 border-[#C9A86C]"
                                  : "text-black/80 hover:bg-black/15 hover:text-black"
                              }
                            `}
                          >
                            {item.label}
                          </button>
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}

          {/* Footer */}
          <div className="mt-auto px-4 py-3 border-t border-black/20">
            <p className="text-black/50 text-xs font-mono">
              v1.0.0 · OpenCV + React
            </p>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
