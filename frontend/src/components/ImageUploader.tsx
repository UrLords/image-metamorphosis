// src/components/ImageUploader.tsx
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, Image as ImageIcon } from "lucide-react";

interface ImageUploaderProps {
  imageUrl: string | null;
  onImageChange: (dataUrl: string) => void;
  label?: string;
}

export default function ImageUploader({
  imageUrl,
  onImageChange,
  label = "Upload Gambar",
}: ImageUploaderProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => onImageChange(reader.result as string);
      reader.readAsDataURL(file);
    },
    [onImageChange],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"] },
    maxFiles: 1,
  });

  return (
    <div className="w-full">
      <p className="text-xs font-medium text-muted mb-2 uppercase tracking-wider">
        {label}
      </p>

      {imageUrl ? (
        /* Preview mode */
        <div className="relative group rounded-xl overflow-hidden border border-border bg-card">
          <img
            src={imageUrl}
            alt="Input"
            className="w-full object-contain max-h-72"
          />
          {/* Overlay to re-upload */}
          <div
            {...getRootProps()}
            className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center cursor-pointer"
          >
            <input {...getInputProps()} />
            <UploadCloud size={28} className="text-accent mb-2" />
            <p className="text-sm text-white font-medium">Ganti Gambar</p>
          </div>
        </div>
      ) : (
        /* Drop zone */
        <div
          {...getRootProps()}
          className={`
            w-full rounded-xl border-2 border-dashed transition-all cursor-pointer
            flex flex-col items-center justify-center py-10 gap-3
            ${isDragActive ? "dropzone-active border-accent" : "border-border hover:border-accent/50 bg-card/50"}
          `}
        >
          <input {...getInputProps()} />
          <div className="p-3 rounded-full bg-accent/10 border border-accent/30">
            {isDragActive ? (
              <UploadCloud size={24} className="text-accent" />
            ) : (
              <ImageIcon size={24} className="text-accent/70" />
            )}
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-white">
              {isDragActive ? "Lepas di sini!" : "Drag & Drop gambar"}
            </p>
            <p className="text-xs text-muted mt-1">
              atau klik untuk pilih file
            </p>
            <p className="text-xs text-muted/60 mt-1">JPG, PNG, BMP, WebP</p>
          </div>
        </div>
      )}
    </div>
  );
}
