import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

// ── Brightness ──────────────────────────────────────
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

// ── Contrast ────────────────────────────────────────
export function ContrastPage() {
  const [alpha, setAlpha] = useState(150);
  return (
    <PageLayout
      title="Contrast (Kontras)"
      subtitle="Kalikan setiap piksel dengan faktor α untuk mengontrol rentang dinamis."
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
            ? "↑ Kontras meningkat"
            : alpha < 100
              ? "↓ Kontras menurun"
              : "= Tidak berubah"}
        </p>
      </div>
    </PageLayout>
  );
}

// ── Negative ────────────────────────────────────────
export function NegativePage() {
  return (
    <PageLayout
      title="Citra Negatif"
      subtitle="Inversi semua nilai piksel: g(x,y) = 255 − f(x,y)."
      operation="negative"
      getParams={() => ({})}
    >
      <p className="text-xs text-muted">Tidak ada parameter. Klik proses.</p>
    </PageLayout>
  );
}

// ── Thresholding ────────────────────────────────────
export function ThresholdingPage() {
  const [threshold, setThreshold] = useState(128);
  const [mode, setMode] = useState("binary");
  return (
    <PageLayout
      title="Thresholding (Binarisasi)"
      subtitle="Konversi gambar ke biner (hitam-putih) menggunakan ambang batas T."
      operation="thresholding"
      getParams={() => ({ threshold, mode })}
    >
      <Select
        label="Mode"
        value={mode}
        options={[
          { value: "binary", label: "Binary (≥T → putih)" },
          { value: "binary_inv", label: "Binary Inv (≥T → hitam)" },
          { value: "otsu", label: "Otsu (T otomatis)" },
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
          Otsu menghitung T optimal via variance antar kelas.
        </p>
      )}
    </PageLayout>
  );
}

// ── Saturation ────────────────────────────────
export function SaturationPage() {
  const [sat, setSat] = useState(50);
  return (
    <PageLayout
      title="Saturation (Kejenuhan Warna)"
      subtitle="Ubah intensitas warna via ruang HSV. +100 = vivid, -100 = grayscale."
      operation="saturation"
      getParams={() => ({ saturation: sat })}
    >
      <Slider
        label="Saturation"
        value={sat}
        min={-100}
        max={100}
        step={5}
        onChange={setSat}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          scale = 1 + {sat}/100 = {(1 + sat / 100).toFixed(2)}
        </p>
        <p>
          {sat > 0
            ? "🎨 Warna lebih jenuh/vivid"
            : sat < 0
              ? "🩶 Warna memudar ke grayscale"
              : "= Tidak berubah"}
        </p>
        <p className="text-accent/70">
          Proses: BGR → HSV → S × scale → HSV → BGR
        </p>
      </div>
    </PageLayout>
  );
}

// ── Hue Shift ─────────────────────────────────
export function HuePage() {
  const [hue, setHue] = useState(60);
  return (
    <PageLayout
      title="Hue Shift (Pergeseran Warna)"
      subtitle="Putar roda warna: merah→kuning→hijau→biru→ungu→merah."
      operation="hue_shift"
      getParams={() => ({ hue })}
    >
      <Slider
        label="Hue Shift (°)"
        value={hue}
        min={-180}
        max={180}
        step={10}
        unit="°"
        onChange={setHue}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          Δh = {hue}° → OpenCV skala ½ = {Math.floor(hue / 2)}
        </p>
        <p>0° = tidak berubah · ±180° = warna terbalik</p>
        <div className="flex gap-1 mt-2 flex-wrap">
          {["🔴 0°", "🟠 30°", "🟡 60°", "🟢 120°", "🔵 180°", "🟣 240°"].map(
            (c) => (
              <span
                key={c}
                className="text-xs px-2 py-0.5 rounded bg-white/5 text-muted"
              >
                {c}
              </span>
            ),
          )}
        </div>
      </div>
    </PageLayout>
  );
}

// ── Opacity ───────────────────────────────────
export function OpacityPage() {
  const [opacity, setOpacity] = useState(60);
  const [bg, setBg] = useState("white");
  return (
    <PageLayout
      title="Opacity (Transparansi)"
      subtitle="Blend gambar dengan background solid. Simulasi transparansi tanpa alpha channel."
      operation="opacity"
      getParams={() => ({ opacity, bg_color: bg })}
    >
      <Slider
        label="Opacity (%)"
        value={opacity}
        min={0}
        max={100}
        step={5}
        unit="%"
        onChange={setOpacity}
      />
      <Select
        label="Warna Background"
        value={bg}
        options={[
          { value: "white", label: "Putih (cocok untuk kertas)" },
          { value: "black", label: "Hitam (cocok untuk layar)" },
        ]}
        onChange={setBg}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3">
        <p>
          α = {opacity}/100 = {(opacity / 100).toFixed(2)}
        </p>
        <p>
          g = {(opacity / 100).toFixed(2)}×f + {(1 - opacity / 100).toFixed(2)}
          ×B
        </p>
      </div>
    </PageLayout>
  );
}

// ── Sharpness ─────────────────────────────────
export function SharpnessPage() {
  const [amount, setAmount] = useState(100);
  return (
    <PageLayout
      title="Sharpness (Ketajaman) — Unsharp Masking"
      subtitle="Pertegas detail gambar dengan menambah kembali detail mask ke gambar asli."
      operation="sharpness"
      getParams={() => ({ amount: amount / 100 })}
    >
      <Slider
        label="Amount"
        value={amount}
        min={0}
        max={300}
        step={10}
        unit="%"
        onChange={setAmount}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>a = {(amount / 100).toFixed(2)}</p>
        <p>g = f + {(amount / 100).toFixed(2)} × (f − GaussianBlur(f))</p>
        <p className="text-accent/70">
          Semakin besar amount, semakin tajam (dan berisik).
        </p>
      </div>
    </PageLayout>
  );
}

// ── Default Router ───────────────────────────────────
export default function OperasiTitik({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "contrast":
      return <ContrastPage />;
    case "negative":
      return <NegativePage />;
    case "thresholding":
      return <ThresholdingPage />;
    case "saturation":
      return <SaturationPage />;
    case "hue_shift":
      return <HuePage />;
    case "opacity":
      return <OpacityPage />;
    case "sharpness":
      return <SharpnessPage />;
    default:
      return <BrightnessPage />;
  }
}
