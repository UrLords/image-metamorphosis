import apiClient from "./axiosClient";

export interface HistogramData {
  red: number[];
  green: number[];
  blue: number[];
  luminance: number[];
}

export type HistogramPayload = HistogramData | number[];

export interface Explanation {
  title: string;
  formula: string;
  description: string;
  steps: string[];
  kernel?: number[][] | null;
  pixel_before?: number[][];
  pixel_after?: number[][];
  histogram_before?: HistogramPayload;
  histogram_after?: HistogramPayload;
  matrix?: number[][];
  image_info?: {
    width: number;
    height: number;
    mode: string;
    size_kb: number;
  };
  pipeline?: Array<{ name: string; beta: number; alpha: number }>;
  code_snippet?: string;
}

export interface ProcessRequest {
  operation: string;
  image: string;
  params: Record<string, unknown>;
}

export interface ProcessResponse {
  before: string;
  after: string;
  explanation: Explanation;
}

export async function processImage(req: ProcessRequest): Promise<ProcessResponse> {
  const res = await apiClient.post<ProcessResponse>("/process", req);
  return res.data;
}

export async function healthCheck(): Promise<boolean> {
  try {
    await apiClient.get("/health");
    return true;
  } catch {
    return false;
  }
}
