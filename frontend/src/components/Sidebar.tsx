import { motion, AnimatePresence } from "framer-motion";
import {
  ImageIcon,
  Plus,
  RotateCw,
  Dot,
  Filter,
  Wand2,
  ScanLine,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";

const MENU = [
  {
    section: "Dasar Citra",
    icon: ImageIcon,
    items: [{ id: "grayscale", label: "Konversi Grayscale" }],
  },
  {
    section: "Operasi Aritmatika",
    icon: Plus,
    items: [
      { id: "blending", label: "Image Blending" },
      { id: "subtraction", label: "Background Subtraction" },
      { id: "multiply", label: "Image Multiplication" },
      { id: "divide", label: "Image Division" },
    ],
  },
  {
    section: "Geometri",
    icon: RotateCw,
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
    items: [
      { id: "brightness", label: "Brightness" },
      { id: "contrast", label: "Contrast" },
      { id: "negative", label: "Negative" },
      { id: "saturation", label: "Saturation" },
      { id: "hue_shift", label: "Hue Shift" },
      { id: "opacity", label: "Opacity" },
      { id: "sharpness", label: "Sharpness" },
    ],
  },
  {
    section: "Operasi Spasial",
    icon: Filter,
    items: [
      { id: "mean_filter", label: "Mean Filter" },
      { id: "gaussian_blur", label: "Gaussian Blur" },
      { id: "median_filter", label: "Median Filter" },
    ],
  },
  {
    section: "Morfologi Citra",
    icon: ImageIcon,
    items: [
      { id: "morphology", label: "Morphology" },
      { id: "zhang_suen", label: "Thinning Zhang-Suen" },
    ],
  },
  {
    section: "Deteksi Tepi",
    icon: Filter,
    items: [
      { id: "sobel", label: "Sobel Edge Detection" },
      { id: "edge_detection", label: "Edge Detection" },
    ],
  },
  {
    section: "Segmentasi Citra",
    icon: Dot,
    items: [{ id: "segmentation", label: "Segmentasi Citra" }],
  },
  {
    section: "Scan Dokumen",
    icon: ScanLine,
    items: [{ id: "scan_document", label: "Scan & Restore" }],
  },
  {
    section: "Advanced Editor",
    icon: Wand2,
    items: [{ id: "advanced_editor", label: "Photo Editor" }],
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
          className="fixed bottom-0 left-0 top-14 z-40 flex w-64 flex-col overflow-y-auto py-4"
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
                <button
                  type="button"
                  onClick={() => toggle(group.section)}
                  className="flex w-full items-center justify-between px-4 py-2.5 transition-colors hover:bg-black/10"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon size={15} className="flex-shrink-0 text-black/70" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-black">
                      {group.section}
                    </span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown size={14} className="text-black/60" />
                  ) : (
                    <ChevronRight size={14} className="text-black/60" />
                  )}
                </button>

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
                            type="button"
                            onClick={() => onSelectOperation(item.id)}
                            className={`w-full py-2 pl-10 pr-4 text-left text-sm transition-all ${
                              isActive
                                ? "border-r-2 border-[#C9A86C] bg-[#0C1014] font-medium text-[#C9A86C]"
                                : "text-black/80 hover:bg-black/15 hover:text-black"
                            }`}
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

          <div className="mt-auto border-t border-black/20 px-4 py-3">
            <p className="font-mono text-xs text-black/50">
              v1.0.0 - OpenCV + React
            </p>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
