// src/pages/StudiKasus.tsx
import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider } from "../components/Controls";

export default function StudiKasus() {
  const [beta, setBeta] = useState(30);
  const [alpha, setAlpha] = useState(130);

  return (
    <PageLayout
      title="Studi Kasus: Photo Enhancement"
      subtitle="Pipeline lengkap untuk meningkatkan foto gelap: Brightness → Contrast → Unsharp Masking → Median Denoise."
      operation="enhance_pipeline"
      getParams={() => ({ beta, alpha: alpha / 100 })}
    >
      <Slider
        label="Tambahan Kecerahan (β)"
        value={beta}
        min={0}
        max={100}
        step={5}
        onChange={setBeta}
      />
      <Slider
        label="Faktor Kontras (α)"
        value={alpha}
        min={100}
        max={250}
        step={10}
        unit="%"
        onChange={setAlpha}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p className="text-accent font-semibold mb-2">Pipeline:</p>
        <p>1. Brightness: g₁ = f + {beta}</p>
        <p>2. Contrast: g₂ = {(alpha / 100).toFixed(2)} × g₁</p>
        <p>3. Sharpening: g₃ = 1.5·g₂ − 0.5·Blur(g₂)</p>
        <p>4. Denoising: g₄ = Median(g₃, 3×3)</p>
      </div>
    </PageLayout>
  );
}
