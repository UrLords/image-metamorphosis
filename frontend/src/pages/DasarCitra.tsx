// src/pages/DasarCitra.tsx
import PageLayout from "../components/PageLayout";

export default function DasarCitra() {
  return (
    <PageLayout
      title="Dasar Pengolahan Citra"
      subtitle="Konversi gambar ke Grayscale menggunakan formula luminance. Lihat matriks piksel asli dan hasil konversi."
      operation="grayscale"
      getParams={() => ({})}
    >
      {/* Tidak ada parameter tambahan untuk grayscale */}
      <p className="text-xs text-muted">
        Tidak ada parameter yang diperlukan. Klik proses untuk mengkonversi
        gambar ke grayscale.
      </p>
    </PageLayout>
  );
}
