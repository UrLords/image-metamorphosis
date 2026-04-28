// src/pages/OperasiTitik.tsx
import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

// ── Brightness ───────────────────────────────────────────────
export function BrightnessPage() {
  const [beta, setBeta] = useState(50);
  return (
    <PageLayout
      title="Brightness (Kecerahan)"
      subtitle="Tambahkan atau kurangi nilai konstan β pada setiap piksel."
      operation="brightness"
      getParams={() => ({ beta })}
    >
      <Slider
        label="Beta (β)"
        value={beta}
        min={-100}
        max={100}
        step={5}
        onChange={setBeta}
      />
      <p className="text-xs text-muted">
        β positif = lebih terang · β negatif = lebih gelap
      </p>
    </PageLayout>
  );
}

// ── Contrast ─────────────────────────────────────────────────
export function ContrastPage() {
  const [alpha, setAlpha] = useState(150);
  return (
    <PageLayout
      title="Contrast (Kontras)"
      subtitle="Kalikan setiap piksel dengan faktor α untuk mengontrol rentang dinamis citra."
      operation="contrast"
      getParams={() => ({ alpha: alpha / 100 })}
    >
      <Slider
        label="Alpha (α)"
        value={alpha}
        min={50}
        max={300}
        step={10}
        unit="%"
        onChange={setAlpha}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3">
        <p>α = {(alpha / 100).toFixed(2)}</p>
        <p>
          {alpha > 100
            ? "Kontras meningkat"
            : alpha < 100
              ? "Kontras menurun"
              : "Tidak ada perubahan"}
        </p>
      </div>
    </PageLayout>
  );
}

// ── Negative ─────────────────────────────────────────────────
export function NegativePage() {
  return (
    <PageLayout
      title="Citra Negatif"
      subtitle="Inversi semua nilai piksel: g(x,y) = 255 − f(x,y). Analog foto negatif film."
      operation="negative"
      getParams={() => ({})}
    >
      <p className="text-xs text-muted">Tidak ada parameter yang diperlukan.</p>
    </PageLayout>
  );
}

// ── Thresholding ─────────────────────────────────────────────
export function ThresholdingPage() {
  const [threshold, setThreshold] = useState(128);
  const [mode, setMode] = useState("binary");
  return (
    <PageLayout
      title="Thresholding (Binarisasi)"
      subtitle="Konversi gambar ke citra biner (hitam-putih) menggunakan nilai ambang batas T."
      operation="thresholding"
      getParams={() => ({ threshold, mode })}
    >
      <Select
        label="Mode"
        value={mode}
        options={[
          { value: "binary", label: "Binary (> T → putih)" },
          { value: "binary_inv", label: "Binary Inv (> T → hitam)" },
          { value: "otsu", label: "Otsu (otomatis)" },
        ]}
        onChange={setMode}
      />
      {mode !== "otsu" && (
        <Slider
          label="Threshold (T)"
          value={threshold}
          min={0}
          max={255}
          step={5}
          onChange={setThreshold}
        />
      )}
      {mode === "otsu" && (
        <p className="text-xs text-accent">
          Otsu menghitung T optimal otomatis menggunakan variance antar kelas.
        </p>
      )}
    </PageLayout>
  );
}

// ── Default ───────────────────────────────────────────────────
export default function OperasiTitik({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "contrast":
      return <ContrastPage />;
    case "negative":
      return <NegativePage />;
    case "thresholding":
      return <ThresholdingPage />;
    default:
      return <BrightnessPage />;
  }
}
