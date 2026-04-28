// src/pages/Geometri.tsx
import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

// ── Rotasi ──────────────────────────────────────────────────
export function RotasiPage() {
  const [angle, setAngle] = useState(45);
  return (
    <PageLayout
      title="Rotasi"
      subtitle="Rotasi gambar terhadap titik pusat menggunakan matriks rotasi 2D."
      operation="rotation"
      getParams={() => ({ angle })}
    >
      <Slider
        label="Sudut Rotasi"
        value={angle}
        min={-180}
        max={180}
        step={5}
        unit="°"
        onChange={setAngle}
      />
    </PageLayout>
  );
}

// ── Scaling ─────────────────────────────────────────────────
export function ScalingPage() {
  const [sx, setSx] = useState(150);
  const [sy, setSy] = useState(150);
  return (
    <PageLayout
      title="Scaling (Resize)"
      subtitle="Ubah ukuran gambar dengan faktor skala pada sumbu X dan Y."
      operation="scaling"
      getParams={() => ({ sx: sx / 100, sy: sy / 100 })}
    >
      <Slider
        label="Skala X"
        value={sx}
        min={25}
        max={300}
        step={5}
        unit="%"
        onChange={setSx}
      />
      <Slider
        label="Skala Y"
        value={sy}
        min={25}
        max={300}
        step={5}
        unit="%"
        onChange={setSy}
      />
    </PageLayout>
  );
}

// ── Translasi ────────────────────────────────────────────────
export function TranslasiPage() {
  const [tx, setTx] = useState(50);
  const [ty, setTy] = useState(50);
  return (
    <PageLayout
      title="Translasi"
      subtitle="Geser gambar sejauh tx piksel ke kanan dan ty piksel ke bawah."
      operation="translation"
      getParams={() => ({ tx, ty })}
    >
      <Slider
        label="Translasi X (tx)"
        value={tx}
        min={-200}
        max={200}
        step={10}
        unit="px"
        onChange={setTx}
      />
      <Slider
        label="Translasi Y (ty)"
        value={ty}
        min={-200}
        max={200}
        step={10}
        unit="px"
        onChange={setTy}
      />
    </PageLayout>
  );
}

// ── Flip ─────────────────────────────────────────────────────
export function FlipPage() {
  const [mode, setMode] = useState("horizontal");
  return (
    <PageLayout
      title="Flip (Cermin)"
      subtitle="Cerminkan gambar secara horizontal, vertikal, atau keduanya."
      operation="flip"
      getParams={() => ({ mode })}
    >
      <Select
        label="Arah Flip"
        value={mode}
        options={[
          { value: "horizontal", label: "Horizontal (kiri-kanan)" },
          { value: "vertical", label: "Vertikal (atas-bawah)" },
          { value: "both", label: "Keduanya" },
        ]}
        onChange={setMode}
      />
    </PageLayout>
  );
}

// ── Default export ────────────────────────────────────────────
export default function Geometri({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "scaling":
      return <ScalingPage />;
    case "translation":
      return <TranslasiPage />;
    case "flip":
      return <FlipPage />;
    default:
      return <RotasiPage />;
  }
}
