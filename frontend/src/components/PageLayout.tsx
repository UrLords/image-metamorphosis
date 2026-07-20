import { motion } from "framer-motion";
import { useState } from "react";
import ImageUploader from "./ImageUploader";
import BeforeAfter from "./BeforeAfter";
import ExplanationPanel from "./ExplanationPanel";
import { ProcessButton, ErrorBanner } from "./Controls";
import { processImage, type Explanation } from "../api/imageApi";
import { useAuth } from "../context/AuthContext";

interface PageLayoutProps {
  title: string;
  subtitle: string;
  operation: string;
  getParams: () => Record<string, unknown>;
  children: React.ReactNode;
  secondImageNeeded?: boolean;
}

export default function PageLayout({
  title,
  subtitle,
  operation,
  getParams,
  children,
  secondImageNeeded = false,
}: PageLayoutProps) {
  const { requireAuth } = useAuth();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [secondUrl, setSecondUrl] = useState<string | null>(null);
  const [afterUrl, setAfterUrl] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async () => {
    if (!imageUrl) {
      setError("Upload gambar terlebih dahulu!");
      return;
    }
    if (!requireAuth()) return;
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = getParams();
      if (secondImageNeeded && secondUrl) params.second_image = secondUrl;

      const res = await processImage({ operation, image: imageUrl, params });
      setAfterUrl(res.after);
      setExplanation(res.explanation);
    } catch (e: unknown) {
      const err = e as {
        response?: { status?: number; data?: { error?: string } };
        message?: string;
      };
      const status = err.response?.status;
      const serverMessage = err.response?.data?.error;
      const fallback = err.message || String(e);

      if (status && serverMessage) {
        setError(`Error ${status}: ${serverMessage}`);
      } else {
        setError(
          `Error: ${fallback}. Pastikan backend Flask sudah berjalan dan VITE_API_URL sudah benar.`,
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      <div className="border-b border-border pb-4">
        <h2
          className="text-2xl font-bold text-white"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          {title}
        </h2>
        <p className="text-sm text-muted mt-1">{subtitle}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-1 space-y-4">
          <div className="rounded-xl border border-border bg-card p-4 space-y-4">
            <ImageUploader imageUrl={imageUrl} onImageChange={setImageUrl} />
            {secondImageNeeded && (
              <ImageUploader
                imageUrl={secondUrl}
                onImageChange={setSecondUrl}
                label="Gambar Kedua (opsional)"
              />
            )}
          </div>

          {children && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-4">
              <p className="text-xs font-semibold text-muted uppercase tracking-widest">
                Parameter
              </p>
              {children}
            </div>
          )}

          {error && <ErrorBanner message={error} />}
          <ProcessButton
            onClick={handleProcess}
            isLoading={isLoading}
            disabled={!imageUrl}
          />
        </div>

        <div className="xl:col-span-2 space-y-6">
          <div className="rounded-xl border border-border bg-card p-4">
            <BeforeAfter
              before={imageUrl}
              after={afterUrl}
              isLoading={isLoading}
            />
          </div>
          <ExplanationPanel explanation={explanation} />
        </div>
      </div>
    </motion.div>
  );
}
