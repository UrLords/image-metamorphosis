import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider } from "../components/Controls";

// Blending
export function BlendingPage() {
  const [alpha, setAlpha] = useState(50);

  return (
    <PageLayout
      title="Image Blending"
      subtitle="Menggabungkan dua gambar dengan bobot alpha dan (1 - alpha). Upload gambar kedua atau biarkan kosong untuk blend dengan blur."
      operation="blending"
      getParams={() => ({ alpha: alpha / 100 })}
      secondImageNeeded={true}
    >
      <Slider
        label="Alpha"
        value={alpha}
        min={0}
        max={100}
        step={1}
        unit="%"
        onChange={setAlpha}
      />

      <div className="text-xs text-muted space-y-0.5 bg-[#0C1014] rounded-lg p-3">
        <p>alpha = {(alpha / 100).toFixed(2)} untuk gambar pertama</p>
        <p>1 - alpha = {(1 - alpha / 100).toFixed(2)} untuk gambar kedua</p>
      </div>
    </PageLayout>
  );
}

// Background subtraction
export function SubtractionPage() {
  return (
    <PageLayout
      title="Background Subtraction"
      subtitle="Mendeteksi foreground dengan mengurangi background (versi blur berat) dari gambar asli."
      operation="subtraction"
      getParams={() => ({})}
    >
      <p className="text-xs text-muted">
        Background dihitung otomatis menggunakan Gaussian Blur 51x51 yang sangat
        smooth.
      </p>
    </PageLayout>
  );
}

// Multiplication
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
        <p>g(x,y) = f1(x,y) x f2(x,y)</p>
      </div>
    </PageLayout>
  );
}

// Division
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
        <p>g(x,y) = f1(x,y) / f2(x,y)</p>
      </div>
    </PageLayout>
  );
}

// Router
export default function OperasiAritmatika({ subpage }: { subpage?: string }) {
  if (subpage === "subtraction") return <SubtractionPage />;

  if (subpage === "multiply") return <MultiplyPage />;

  if (subpage === "divide") return <DividePage />;

  return <BlendingPage />;
}
