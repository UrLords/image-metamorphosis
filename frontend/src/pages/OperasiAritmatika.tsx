// src/pages/OperasiAritmatika.tsx
import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider } from "../components/Controls";

// ─────────────────────────────────────────────────────────────
// Blending Page
// ─────────────────────────────────────────────────────────────
export function BlendingPage() {
  const [alpha, setAlpha] = useState(50);

  return (
    <PageLayout
      title="Image Blending"
      subtitle="Menggabungkan dua gambar dengan bobot α dan (1-α). Upload gambar kedua atau biarkan kosong untuk blend dengan blur."
      operation="blending"
      getParams={() => ({ alpha: alpha / 100 })}
      secondImageNeeded={true}
    >
      <Slider
        label="Alpha (α)"
        value={alpha}
        min={0}
        max={100}
        step={1}
        unit="%"
        onChange={setAlpha}
      />

      <div className="text-xs text-muted space-y-0.5 bg-[#0C1014] rounded-lg p-3">
        <p>α = {(alpha / 100).toFixed(2)} → gambar pertama</p>
        <p>1−α = {(1 - alpha / 100).toFixed(2)} → gambar kedua</p>
      </div>
    </PageLayout>
  );
}

// ─────────────────────────────────────────────────────────────
// Subtraction Page
// ─────────────────────────────────────────────────────────────
export function SubtractionPage() {
  return (
    <PageLayout
      title="Background Subtraction"
      subtitle="Mendeteksi foreground dengan mengurangi background (versi blur berat) dari gambar asli."
      operation="subtraction"
      getParams={() => ({})}
    >
      <p className="text-xs text-muted">
        Background dihitung otomatis menggunakan Gaussian Blur 51×51 yang sangat
        smooth.
      </p>
    </PageLayout>
  );
}

// ─────────────────────────────────────────────────────────────
// Multiply Page
// ─────────────────────────────────────────────────────────────
export function MultiplyPage() {
  return (
    <PageLayout
      title="Image Multiplication"
      subtitle="Mengalikan setiap piksel dari dua gambar untuk menghasilkan efek overlap dan darkening."
      operation="multiply"
      getParams={() => ({})}
      secondImageNeeded={true}
    >
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3">
        <p>Formula:</p>
        <p>g(x,y) = f₁(x,y) × f₂(x,y)</p>
      </div>
    </PageLayout>
  );
}

// ─────────────────────────────────────────────────────────────
// Divide Page
// ─────────────────────────────────────────────────────────────
export function DividePage() {
  return (
    <PageLayout
      title="Image Division"
      subtitle="Membagi setiap piksel gambar pertama dengan gambar kedua."
      operation="divide"
      getParams={() => ({})}
      secondImageNeeded={true}
    >
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3">
        <p>Formula:</p>
        <p>g(x,y) = f₁(x,y) / f₂(x,y)</p>
      </div>
    </PageLayout>
  );
}

// ─────────────────────────────────────────────────────────────
// Router
// ─────────────────────────────────────────────────────────────
export default function OperasiAritmatika({ subpage }: { subpage?: string }) {
  if (subpage === "subtraction") return <SubtractionPage />;

  if (subpage === "multiply") return <MultiplyPage />;

  if (subpage === "divide") return <DividePage />;

  return <BlendingPage />;
}
