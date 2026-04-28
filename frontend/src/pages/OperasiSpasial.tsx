// src/pages/OperasiSpasial.tsx
import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

// ── Mean Filter ──────────────────────────────────────────────
export function MeanFilterPage() {
  const [ksize, setKsize] = useState(3);
  return (
    <PageLayout
      title="Mean Filter (Low-pass)"
      subtitle="Gantikan setiap piksel dengan rata-rata tetangganya dalam window k×k. Mengurangi noise acak."
      operation="mean_filter"
      getParams={() => ({ ksize: ksize % 2 === 0 ? ksize + 1 : ksize })}
    >
      <Slider
        label="Ukuran Kernel (k)"
        value={ksize}
        min={3}
        max={15}
        step={2}
        onChange={setKsize}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3">
        <p>
          Kernel: {ksize}×{ksize} = {ksize * ksize} piksel
        </p>
        <p>
          Bobot tiap elemen: 1/{ksize * ksize} ={" "}
          {(1 / (ksize * ksize)).toFixed(4)}
        </p>
      </div>
    </PageLayout>
  );
}

// ── Median Filter ────────────────────────────────────────────
export function MedianFilterPage() {
  const [ksize, setKsize] = useState(3);
  return (
    <PageLayout
      title="Median Filter"
      subtitle="Gantikan setiap piksel dengan nilai median tetangganya. Sangat efektif untuk salt-and-pepper noise."
      operation="median_filter"
      getParams={() => ({ ksize: ksize % 2 === 0 ? ksize + 1 : ksize })}
    >
      <Slider
        label="Ukuran Window (k)"
        value={ksize}
        min={3}
        max={11}
        step={2}
        onChange={setKsize}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3">
        <p>
          Window: {ksize}×{ksize} = {ksize * ksize} piksel
        </p>
        <p>Tidak menggunakan kernel numerik — menggunakan sorting.</p>
      </div>
    </PageLayout>
  );
}

// ── Sobel ─────────────────────────────────────────────────────
export function SobelPage() {
  const [direction, setDirection] = useState("both");
  return (
    <PageLayout
      title="Sobel Edge Detection"
      subtitle="Deteksi tepi/edge menggunakan gradien first-order. Kernel Sobel 3×3 untuk Gx dan Gy."
      operation="sobel"
      getParams={() => ({ direction })}
    >
      <Select
        label="Arah Deteksi"
        value={direction}
        options={[
          { value: "both", label: "Kedua Arah (|Gx| + |Gy|)" },
          { value: "x", label: "Horizontal (Gx)" },
          { value: "y", label: "Vertikal (Gy)" },
        ]}
        onChange={setDirection}
      />
      <div className="text-xs text-muted space-y-1">
        <p>
          <strong className="text-white">Gx</strong>: mendeteksi tepi vertikal
        </p>
        <p>
          <strong className="text-white">Gy</strong>: mendeteksi tepi horizontal
        </p>
        <p>
          <strong className="text-white">Both</strong>: √(Gx² + Gy²)
        </p>
      </div>
    </PageLayout>
  );
}

// ── Default ───────────────────────────────────────────────────
export default function OperasiSpasial({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "median_filter":
      return <MedianFilterPage />;
    case "sobel":
      return <SobelPage />;
    default:
      return <MeanFilterPage />;
  }
}
