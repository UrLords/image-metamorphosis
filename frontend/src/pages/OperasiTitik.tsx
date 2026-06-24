import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

export function BrightnessPage() {
  const [beta, setBeta] = useState(50);

  return (
    <PageLayout
      title="Brightness (Kecerahan)"
      subtitle="Menambah atau mengurangi nilai konstan beta pada setiap piksel."
      operation="brightness"
      getParams={() => ({ beta })}
    >
      <Slider
        label="Beta"
        value={beta}
        min={-100}
        max={100}
        step={5}
        onChange={setBeta}
      />
      <p className="text-xs text-muted">
        Beta positif membuat gambar lebih terang, beta negatif membuat gambar
        lebih gelap.
      </p>
    </PageLayout>
  );
}

export function ContrastPage() {
  const [alpha, setAlpha] = useState(150);

  return (
    <PageLayout
      title="Contrast (Kontras)"
      subtitle="Mengalikan setiap piksel dengan faktor alpha untuk mengatur rentang dinamis."
      operation="contrast"
      getParams={() => ({ alpha: alpha / 100 })}
    >
      <Slider
        label="Alpha"
        value={alpha}
        min={50}
        max={300}
        step={10}
        unit="%"
        onChange={setAlpha}
      />
      <div className="rounded-lg bg-[#0C1014] p-3 text-xs text-muted">
        <p>alpha = {(alpha / 100).toFixed(2)}</p>
        <p>
          {alpha > 100
            ? "Kontras meningkat"
            : alpha < 100
              ? "Kontras menurun"
              : "Tidak berubah"}
        </p>
      </div>
    </PageLayout>
  );
}

export function NegativePage() {
  return (
    <PageLayout
      title="Citra Negatif"
      subtitle="Inversi semua nilai piksel: g(x,y) = 255 - f(x,y)."
      operation="negative"
      getParams={() => ({})}
    >
      <p className="text-xs text-muted">
        Tidak ada parameter. Klik proses untuk melihat hasil inversi.
      </p>
    </PageLayout>
  );
}

export function ThresholdingPage() {
  const [threshold, setThreshold] = useState(128);
  const [mode, setMode] = useState("binary");

  return (
    <PageLayout
      title="Thresholding (Binarisasi)"
      subtitle="Memisahkan piksel menjadi hitam-putih berdasarkan ambang batas T."
      operation="thresholding"
      getParams={() => ({ threshold, mode })}
    >
      <Select
        label="Mode"
        value={mode}
        options={[
          { value: "binary", label: "Binary: >= T menjadi putih" },
          { value: "binary_inv", label: "Binary Inv: >= T menjadi hitam" },
          { value: "otsu", label: "Otsu: T otomatis" },
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
          Otsu mencari threshold optimal dari histogram intensitas.
        </p>
      )}
    </PageLayout>
  );
}

export function SaturationPage() {
  const [sat, setSat] = useState(50);
  const scale = 1 + sat / 100;

  return (
    <PageLayout
      title="Saturation (Kejenuhan Warna)"
      subtitle="Mengatur kekuatan warna dengan memodifikasi channel S pada ruang warna HSV."
      operation="saturation"
      getParams={() => ({ saturation: sat })}
    >
      <Slider
        label="Saturation"
        value={sat}
        min={-100}
        max={100}
        step={5}
        unit="%"
        onChange={setSat}
      />
      <div className="space-y-1 rounded-lg bg-[#0C1014] p-3 text-xs text-muted">
        <p>scale = 1 + saturation/100 = {scale.toFixed(2)}</p>
        <p>
          S lebih besar membuat warna lebih vivid. S lebih kecil membuat warna
          mendekati grayscale.
        </p>
        <p className="text-accent/70">
          Proses: BGR ke HSV, ubah S, lalu kembali ke BGR.
        </p>
      </div>
    </PageLayout>
  );
}

export function HuePage() {
  const [hue, setHue] = useState(60);

  return (
    <PageLayout
      title="Hue Shift (Pergeseran Warna)"
      subtitle="Memutar warna pada roda hue tanpa mengubah kecerahan utama gambar."
      operation="hue_shift"
      getParams={() => ({ hue })}
    >
      <Slider
        label="Hue Shift"
        value={hue}
        min={-180}
        max={180}
        step={10}
        unit="deg"
        onChange={setHue}
      />
      <div className="space-y-1 rounded-lg bg-[#0C1014] p-3 text-xs text-muted">
        <p>
          Delta h = {hue} deg. OpenCV menyimpan hue pada skala 0-180, jadi
          pergeseran internal = {Math.floor(hue / 2)}.
        </p>
        <p>
          0 deg tidak berubah. Pergeseran positif/negatif memutar seluruh warna
          pada roda hue.
        </p>
        <p className="text-accent/70">
          Contoh: merah bisa bergeser menuju kuning, hijau, biru, lalu kembali
          ke merah.
        </p>
      </div>
    </PageLayout>
  );
}

export function OpacityPage() {
  const [opacity, setOpacity] = useState(60);
  const [bg, setBg] = useState("white");
  const alpha = opacity / 100;

  return (
    <PageLayout
      title="Opacity (Transparansi)"
      subtitle="Mencampur gambar dengan background solid untuk mensimulasikan transparansi."
      operation="opacity"
      getParams={() => ({ opacity, bg_color: bg })}
    >
      <Slider
        label="Opacity"
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
          { value: "white", label: "Putih" },
          { value: "black", label: "Hitam" },
        ]}
        onChange={setBg}
      />
      <div className="rounded-lg bg-[#0C1014] p-3 text-xs text-muted">
        <p>alpha = {alpha.toFixed(2)}</p>
        <p>g = alpha x f + (1 - alpha) x background</p>
      </div>
    </PageLayout>
  );
}

export function SharpnessPage() {
  const [amount, setAmount] = useState(100);
  const a = amount / 100;

  return (
    <PageLayout
      title="Sharpness (Ketajaman) - Unsharp Masking"
      subtitle="Mempertegas detail dengan menambahkan kembali detail mask ke gambar asli."
      operation="sharpness"
      getParams={() => ({ amount: a })}
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
      <div className="space-y-1 rounded-lg bg-[#0C1014] p-3 text-xs text-muted">
        <p>a = {a.toFixed(2)}</p>
        <p>g = f + a x (f - GaussianBlur(f))</p>
        <p className="text-accent/70">
          Semakin besar amount, detail makin tajam tetapi noise juga bisa ikut
          menguat.
        </p>
      </div>
    </PageLayout>
  );
}

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
