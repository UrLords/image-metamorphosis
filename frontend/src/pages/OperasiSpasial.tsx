import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

// ── Mean Filter ─────────────────────────────────────
export function MeanFilterPage() {
  const [ksize, setKsize] = useState(3);
  const k = ksize % 2 === 0 ? ksize + 1 : ksize;
  return (
    <PageLayout
      title="Mean Filter (Low-pass)"
      subtitle="Gantikan setiap piksel dengan rata-rata tetangganya dalam window k×k."
      operation="mean_filter"
      getParams={() => ({ ksize: k })}
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
          Kernel: {k}×{k} = {k * k} piksel
        </p>
        <p>
          Bobot tiap elemen: 1/{k * k} = {(1 / (k * k)).toFixed(4)}
        </p>
      </div>
    </PageLayout>
  );
}

// ── Gaussian Blur ─────────────────────────────
export function GaussianBlurPage() {
  const [sigma, setSigma] = useState(20);
  const sigmaVal = sigma / 10;
  const ksize = Math.max(3, Math.floor(sigmaVal * 3) * 2 + 1);
  return (
    <PageLayout
      title="Gaussian Blur"
      subtitle="Blur berbasis distribusi Gaussian. Piksel lebih dekat ke pusat mendapat bobot lebih besar."
      operation="gaussian_blur"
      getParams={() => ({ sigma: sigmaVal })}
    >
      <Slider
        label="Sigma (σ)"
        value={sigma}
        min={5}
        max={100}
        step={5}
        onChange={setSigma}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          σ = {sigmaVal.toFixed(1)}, kernel = {ksize}×{ksize}
        </p>
        <p>G(x,y) = e^(-(x²+y²)/(2σ²)) / (2πσ²)</p>
        <p className="text-accent/70">
          Mean Filter: semua bobot sama.
          <br />
          Gaussian: bobot menurun dari pusat → lebih natural.
        </p>
      </div>
    </PageLayout>
  );
}

// ── Median Filter ───────────────────────────────────
export function MedianFilterPage() {
  const [ksize, setKsize] = useState(3);
  const k = ksize % 2 === 0 ? ksize + 1 : ksize;
  return (
    <PageLayout
      title="Median Filter"
      subtitle="Gantikan setiap piksel dengan nilai median tetangganya. Efektif untuk salt-and-pepper noise."
      operation="median_filter"
      getParams={() => ({ ksize: k })}
    >
      <Slider
        label="Ukuran Window (k)"
        value={ksize}
        min={3}
        max={11}
        step={2}
        onChange={setKsize}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          Window: {k}×{k} = {k * k} piksel
        </p>
        <p>Tidak pakai kernel numerik — gunakan sorting.</p>
        <p className="text-accent/70">
          Kelebihan vs Mean: tahan terhadap outlier ekstrem.
        </p>
      </div>
    </PageLayout>
  );
}

// ── Sobel ───────────────────────────────────────────
export function SobelPage() {
  const [direction, setDirection] = useState("both");
  return (
    <PageLayout
      title="Sobel Edge Detection"
      subtitle="Deteksi tepi via gradien first-order. Kernel 3×3 untuk Gx dan Gy."
      operation="sobel"
      getParams={() => ({ direction })}
    >
      <Select
        label="Arah Deteksi"
        value={direction}
        options={[
          { value: "both", label: "Kedua Arah √(Gx²+Gy²)" },
          { value: "x", label: "Horizontal Gx" },
          { value: "y", label: "Vertikal Gy" },
        ]}
        onChange={setDirection}
      />
      <div className="text-xs text-muted space-y-1">
        <p>
          <strong className="text-white">Gx</strong>: tepi vertikal
        </p>
        <p>
          <strong className="text-white">Gy</strong>: tepi horizontal
        </p>
        <p>
          <strong className="text-white">Both</strong>: √(Gx²+Gy²) — paling
          lengkap
        </p>
      </div>
    </PageLayout>
  );
}

// ── Default Router ───────────────────────────────────
export default function OperasiSpasial({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "gaussian_blur":
      return <GaussianBlurPage />;
    case "median_filter":
      return <MedianFilterPage />;
    case "sobel":
      return <SobelPage />;
    default:
      return <MeanFilterPage />;
  }
}
