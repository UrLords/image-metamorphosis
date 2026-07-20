import { useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import AuthPromptModal from "./components/AuthPromptModal";
import Home from "./pages/Home";
import DasarCitra from "./pages/DasarCitra";
import OperasiAritmatika from "./pages/OperasiAritmatika";
import Geometri from "./pages/Geometri";
import OperasiTitik from "./pages/OperasiTitik";
import OperasiSpasial from "./pages/OperasiSpasial";
import MorfologiCitra from "./pages/MorfologiCitra";
import DeteksiTepi from "./pages/DeteksiTepi";
import SegmentasiCitra from "./pages/SegmentasiCitra";
import AdvancedEditor from "./pages/AdvancedEditor";
import ScanDocument from "./pages/ScanDocument";

const OPERATION_PAGE: Record<string, string> = {
  grayscale: "dasar",
  blending: "aritmatika",
  subtraction: "aritmatika",
  multiply: "aritmatika",
  divide: "aritmatika",
  rotation: "geometri",
  scaling: "geometri",
  translation: "geometri",
  flip: "geometri",
  brightness: "titik",
  contrast: "titik",
  negative: "titik",
  thresholding: "segmentasi",
  saturation: "titik",
  hue_shift: "titik",
  opacity: "titik",
  sharpness: "titik",
  mean_filter: "spasial",
  gaussian_blur: "spasial",
  median_filter: "spasial",
  sobel: "deteksi",
  morphology: "morfologi",
  zhang_suen: "morfologi",
  edge_detection: "deteksi",
  segmentation: "segmentasi",
  scan_document: "scan",
  advanced_editor: "editor",
};

const DEFAULT_OPERATION: Record<string, string> = {
  dasar: "grayscale",
  aritmatika: "blending",
  geometri: "rotation",
  titik: "brightness",
  spasial: "mean_filter",
  morfologi: "morphology",
  deteksi: "edge_detection",
  segmentasi: "segmentation",
  scan: "scan_document",
  editor: "advanced_editor",
};

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(() =>
    window.matchMedia("(min-width: 1024px)").matches,
  );
  const [activePage, setActivePage] = useState("home");
  const [activeOperation, setActiveOperation] = useState("grayscale");
  const [activeSubpage, setActiveSubpage] = useState<string | undefined>(
    undefined,
  );

  const handleNavigate = (page: string) => {
    setActivePage(page);
    setActiveSubpage(undefined);
    if (DEFAULT_OPERATION[page]) setActiveOperation(DEFAULT_OPERATION[page]);
  };

  const handleSelectOperation = (opId: string) => {
    const page = OPERATION_PAGE[opId] || "home";
    setActiveOperation(opId);
    setActivePage(page);
    setActiveSubpage(opId);
  };

  const renderPage = () => {
    switch (activePage) {
      case "home":
        return <Home onNavigate={handleNavigate} />;
      case "dasar":
        return <DasarCitra />;
      case "aritmatika":
        return <OperasiAritmatika subpage={activeSubpage} />;
      case "geometri":
        return <Geometri subpage={activeSubpage} />;
      case "titik":
        return <OperasiTitik subpage={activeSubpage} />;
      case "spasial":
        return <OperasiSpasial subpage={activeSubpage} />;
      case "morfologi":
        return <MorfologiCitra subpage={activeSubpage} />;
      case "deteksi":
        return <DeteksiTepi subpage={activeSubpage} />;
      case "segmentasi":
        return <SegmentasiCitra />;
      case "scan":
        return <ScanDocument />;
      case "editor":
        return <AdvancedEditor />;
      default:
        return <Home onNavigate={handleNavigate} />;
    }
  };

  return (
    <div
      className="min-h-screen bg-bg"
      style={{ fontFamily: "'DM Sans', sans-serif" }}
    >
      <Header
        onNavigate={handleNavigate}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      <Sidebar
        isOpen={sidebarOpen}
        activeOperation={activeOperation}
        onSelectOperation={handleSelectOperation}
      />

      <main
        className={`min-h-screen pt-16 transition-all duration-300 ${
          sidebarOpen ? "lg:ml-[304px]" : ""
        }`}
      >
        <div className="p-6 lg:p-8">{renderPage()}</div>
      </main>
      <AuthPromptModal />
    </div>
  );
}
