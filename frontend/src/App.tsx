import { useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import DasarCitra from "./pages/DasarCitra";
import OperasiAritmatika from "./pages/OperasiAritmatika";
import Geometri from "./pages/Geometri";
import OperasiTitik from "./pages/OperasiTitik";
import OperasiSpasial from "./pages/OperasiSpasial";
import AdvancedEditor from "./pages/AdvancedEditor";

// Mapping operasi → page
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
  thresholding: "titik",
  saturation: "titik",
  hue_shift: "titik",
  opacity: "titik",
  sharpness: "titik",
  mean_filter: "spasial",
  gaussian_blur: "spasial",
  median_filter: "spasial",
  sobel: "spasial",
  advanced_editor: "editor",
};

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activePage, setActivePage] = useState("home");
  const [activeOperation, setActiveOperation] = useState("grayscale");
  const [activeSubpage, setActiveSubpage] = useState<string | undefined>(
    undefined,
  );

  // nav menu
  const handleNavigate = (page: string) => {
    setActivePage(page);
    setActiveSubpage(undefined);
    const defaults: Record<string, string> = {
      dasar: "grayscale",
      aritmatika: "blending",
      geometri: "rotation",
      titik: "brightness",
      spasial: "mean_filter",
      editor: "advanced_editor",
    };
    if (defaults[page]) setActiveOperation(defaults[page]);
  };

  const handleSelectOperation = (opId: string) => {
    const page = OPERATION_PAGE[opId] || "home";

    setActiveOperation(opId);
    setActivePage(page);
    setActiveSubpage(opId);
  };

  // Render halaman berdasarkan activePage + activeSubpage
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
      {/* ── Fixed Header ── */}
      <Header
        activePage={activePage}
        onNavigate={handleNavigate}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* ── Sidebar ── */}
      <Sidebar
        isOpen={sidebarOpen}
        activeOperation={activeOperation}
        onSelectOperation={handleSelectOperation}
      />

      {/* ── Main Content ── */}
      <main
        className="pt-14 transition-all duration-300 min-h-screen"
        style={{ marginLeft: sidebarOpen ? "256px" : "0px" }}
      >
        <div className="p-6">{renderPage()}</div>
      </main>
    </div>
  );
}
