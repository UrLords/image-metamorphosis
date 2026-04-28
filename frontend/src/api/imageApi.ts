// src/api/imageApi.ts
import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export interface Explanation {
  title: string;
  formula: string;
  description: string;
  steps: string[];
  kernel?: number[][] | null;
  pixel_before?: number[][];
  pixel_after?: number[][];
  matrix?: number[][];
  image_info?: {
    width: number;
    height: number;
    mode: string;
    size_kb: number;
  };
  pipeline?: Array<{ name: string; beta: number; alpha: number }>;
}

export interface ProcessResponse {
  before: string;
  after: string;
  explanation: Explanation;
}

export interface ProcessRequest {
  operation: string;
  image: string; // base64 data URL
  params?: Record<string, unknown>;
}

// ── POST /api/process ─────────────────────────────────────────
export async function processImage(
  req: ProcessRequest,
): Promise<ProcessResponse> {
  const res = await api.post<ProcessResponse>("/process", req);
  return res.data;
}

// ── GET /api/health ───────────────────────────────────────────
export async function healthCheck(): Promise<boolean> {
  try {
    await api.get("/health");
    return true;
  } catch {
    return false;
  }
}
