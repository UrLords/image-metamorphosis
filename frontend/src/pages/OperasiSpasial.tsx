import { useState } from "react";
import PageLayout from "../components/PageLayout";
import { Slider, Select } from "../components/Controls";

export function MeanFilterPage() {
  const [ksize, setKsize] = useState(3);
  const k = ksize % 2 === 0 ? ksize + 1 : ksize;

  return (
    <PageLayout
      title="Mean Filter (Low-pass)"
      subtitle="Gantikan setiap piksel dengan rata-rata tetangganya dalam window k x k."
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
          Kernel: {k} x {k} = {k * k} piksel
        </p>
        <p>
          Bobot tiap elemen: 1/{k * k} = {(1 / (k * k)).toFixed(4)}
        </p>
      </div>
    </PageLayout>
  );
}

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
        label="Sigma"
        value={sigma}
        min={5}
        max={100}
        step={5}
        onChange={setSigma}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          sigma = {sigmaVal.toFixed(1)}, kernel = {ksize} x {ksize}
        </p>
        <p>G(x,y) = exp(-(x^2 + y^2) / (2 x sigma^2)) / (2 x pi x sigma^2)</p>
        <p className="text-accent/70">
          Mean Filter: semua bobot sama.
          <br />
          Gaussian: bobot menurun dari pusat, hasil blur lebih natural.
        </p>
      </div>
    </PageLayout>
  );
}

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
          Window: {k} x {k} = {k * k} piksel
        </p>
        <p>Tidak pakai kernel numerik; gunakan sorting.</p>
        <p className="text-accent/70">
          Kelebihan vs Mean: tahan terhadap outlier ekstrem.
        </p>
      </div>
    </PageLayout>
  );
}

export function SobelPage() {
  const [direction, setDirection] = useState("both");

  return (
    <PageLayout
      title="Sobel Edge Detection"
      subtitle="Deteksi tepi via gradien first-order. Kernel 3 x 3 untuk Gx dan Gy."
      operation="sobel"
      getParams={() => ({ direction })}
    >
      <Select
        label="Arah Deteksi"
        value={direction}
        options={[
          { value: "both", label: "Kedua Arah sqrt(Gx^2+Gy^2)" },
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
          <strong className="text-white">Both</strong>: sqrt(Gx^2+Gy^2), paling
          lengkap
        </p>
      </div>
    </PageLayout>
  );
}

export function MorphologyPage() {
  const [mode, setMode] = useState("dilation");
  const [source, setSource] = useState("binary");
  const [ksize, setKsize] = useState(5);
  const [iterations, setIterations] = useState(1);
  const k = ksize % 2 === 0 ? ksize + 1 : ksize;

  const descriptions: Record<string, string> = {
    dilation: "Dilasi menebalkan objek dan membantu menyambungkan gap kecil.",
    erosion: "Erosi menipiskan objek dengan mengurangi piksel pada kontur.",
    opening:
      "Opening menghapus noise kecil dan penonjolan tipis: erosi lalu dilasi.",
    closing: "Closing menutup lubang kecil dan gap tipis: dilasi lalu erosi.",
    boundary:
      "Boundary extraction mengambil batas objek: citra asal dikurangi hasil erosi.",
  };

  return (
    <PageLayout
      title="Morphology"
      subtitle="Operasi bentuk objek: dilasi, erosi, opening, closing, dan boundary extraction."
      operation="morphology"
      getParams={() => ({ mode, source, ksize: k, iterations })}
    >
      <Select
        label="Mode Operasi"
        value={mode}
        options={[
          { value: "dilation", label: "Dilasi" },
          { value: "erosion", label: "Erosi" },
          { value: "opening", label: "Opening" },
          { value: "closing", label: "Closing" },
          { value: "boundary", label: "Boundary Extraction" },
        ]}
        onChange={setMode}
      />
      <Select
        label="Sumber Proses"
        value={source}
        options={[
          { value: "binary", label: "Binary Otsu (disarankan)" },
          { value: "grayscale", label: "Grayscale" },
          { value: "color", label: "Color" },
        ]}
        onChange={setSource}
      />
      <Slider
        label="Structuring Element (k)"
        value={ksize}
        min={3}
        max={15}
        step={2}
        onChange={setKsize}
      />
      <Slider
        label="Iterations"
        value={iterations}
        min={1}
        max={5}
        step={1}
        onChange={setIterations}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          Kernel: kotak {k} x {k}, iterations: {iterations}
        </p>
        <p>{descriptions[mode]}</p>
        <p className="text-accent/70">
          Morphology dipakai untuk mengubah bentuk objek pada citra biner atau
          grayscale.
        </p>
      </div>
    </PageLayout>
  );
}

export function ZhangSuenPage() {
  const [invert, setInvert] = useState(false);
  const [maxDim, setMaxDim] = useState(900);

  return (
    <PageLayout
      title="Thinning Zhang-Suen"
      subtitle="Penipisan objek menjadi skeleton satu piksel tanpa menghilangkan struktur utama."
      operation="zhang_suen"
      getParams={() => ({ invert, max_dim: maxDim, max_iterations: 80 })}
    >
      <Select
        label="Objek Utama"
        value={invert ? "dark" : "bright"}
        options={[
          { value: "bright", label: "Objek terang di background gelap" },
          { value: "dark", label: "Objek gelap di background terang" },
        ]}
        onChange={(value) => setInvert(value === "dark")}
      />
      <Slider
        label="Resolusi Kerja"
        value={maxDim}
        min={500}
        max={1400}
        step={100}
        unit="px"
        onChange={setMaxDim}
      />
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          Zhang-Suen memakai dua sub-iterasi berulang untuk menghapus piksel
          batas secara aman.
        </p>
        <p className="text-accent/70">
          Tujuan: objek direduksi menjadi kerangka dasar atau skeleton yang
          mendekati garis sumbu objek.
        </p>
      </div>
    </PageLayout>
  );
}

export function EdgeDetectionPage() {
  const [method, setMethod] = useState("canny");
  const [blur, setBlur] = useState(3);
  const [low, setLow] = useState(60);
  const [high, setHigh] = useState(160);

  return (
    <PageLayout
      title="Edge Detection"
      subtitle="Pendeteksian tepi untuk menemukan batas antar region atau objek."
      operation="edge_detection"
      getParams={() => ({ method, blur, low, high })}
    >
      <Select
        label="Metode"
        value={method}
        options={[
          { value: "canny", label: "Canny (noise-aware)" },
          { value: "sobel", label: "Sobel Gradient" },
          { value: "prewitt", label: "Prewitt Gradient" },
          { value: "roberts", label: "Roberts Diagonal" },
          { value: "laplacian", label: "Laplacian" },
        ]}
        onChange={setMethod}
      />
      <Slider
        label="Smoothing Blur"
        value={blur}
        min={1}
        max={15}
        step={2}
        onChange={setBlur}
      />
      {method === "canny" && (
        <>
          <Slider
            label="Canny Low"
            value={low}
            min={10}
            max={200}
            step={5}
            onChange={setLow}
          />
          <Slider
            label="Canny High"
            value={high}
            min={50}
            max={300}
            step={5}
            onChange={setHigh}
          />
        </>
      )}
      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>
          Tepi curam muncul saat intensitas berubah tajam. Tepi landai berubah
          bertahap.
        </p>
        <p className="text-accent/70">
          Untuk gambar noisy, smoothing sebelum edge detection membuat batas
          objek lebih stabil.
        </p>
      </div>
    </PageLayout>
  );
}

export function SegmentationPage() {
  const [mode, setMode] = useState("otsu_blur");
  const [threshold, setThreshold] = useState(127);
  const [blockSize, setBlockSize] = useState(21);
  const [cValue, setCValue] = useState(5);
  const [clusters, setClusters] = useState(4);
  const [blur, setBlur] = useState(5);

  const isGlobal = mode.startsWith("global_");
  const isAdaptive = mode.startsWith("adaptive_");
  const isOtsuBlur = mode === "otsu_blur";
  const isKMeans = mode === "kmeans";
  const descriptions: Record<string, string> = {
    global_binary:
      "Global threshold memakai satu nilai T untuk seluruh gambar. Cocok jika pencahayaan merata.",
    adaptive_gaussian:
      "Adaptive Gaussian menghitung threshold lokal. Cocok untuk foto dokumen yang pencahayaannya tidak rata.",
    otsu_blur:
      "Otsu + Gaussian otomatis mencari threshold terbaik setelah noise dikurangi. Ini pilihan aman untuk banyak citra grayscale.",
    kmeans:
      "K-Means mengelompokkan piksel warna RGB menjadi beberapa region warna. Cocok untuk segmentasi citra berwarna.",
  };

  return (
    <PageLayout
      title="Segmentasi Citra"
      subtitle="Memisahkan objek atau region berdasarkan intensitas, warna, atau properti homogen lain."
      operation="segmentation"
      getParams={() => ({
        mode,
        threshold,
        block_size: blockSize,
        c: cValue,
        clusters,
        blur,
      })}
    >
      <Select
        label="Teknik Segmentasi"
        value={mode}
        options={[
          { value: "global_binary", label: "Global Thresholding" },
          { value: "adaptive_gaussian", label: "Adaptive Thresholding" },
          { value: "otsu_blur", label: "Otsu Binarization" },
          { value: "kmeans", label: "K-Means Color Segmentation" },
        ]}
        onChange={setMode}
      />

      {isGlobal && (
        <Slider
          label="Threshold"
          value={threshold}
          min={0}
          max={255}
          step={1}
          onChange={setThreshold}
        />
      )}

      {isAdaptive && (
        <>
          <Slider
            label="Block Size"
            value={blockSize}
            min={3}
            max={51}
            step={2}
            onChange={setBlockSize}
          />
          <Slider
            label="C"
            value={cValue}
            min={-20}
            max={20}
            step={1}
            onChange={setCValue}
          />
        </>
      )}

      {isOtsuBlur && (
        <Slider
          label="Gaussian Blur"
          value={blur}
          min={3}
          max={21}
          step={2}
          onChange={setBlur}
        />
      )}

      {isKMeans && (
        <Slider
          label="Cluster K"
          value={clusters}
          min={2}
          max={8}
          step={1}
          onChange={setClusters}
        />
      )}

      <div className="text-xs text-muted bg-[#0C1014] rounded-lg p-3 space-y-1">
        <p>{descriptions[mode]}</p>
        <p className="text-accent/70">
          Segmentasi memisahkan objek/region sebagai tahap awal sebelum
          recognition, image understanding, atau analisis objek.
        </p>
      </div>
    </PageLayout>
  );
}

export default function OperasiSpasial({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "gaussian_blur":
      return <GaussianBlurPage />;
    case "median_filter":
      return <MedianFilterPage />;
    case "sobel":
      return <SobelPage />;
    case "morphology":
      return <MorphologyPage />;
    case "zhang_suen":
      return <ZhangSuenPage />;
    case "edge_detection":
      return <EdgeDetectionPage />;
    case "segmentation":
      return <SegmentationPage />;
    default:
      return <MeanFilterPage />;
  }
}
