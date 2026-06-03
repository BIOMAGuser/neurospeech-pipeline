import { apiFetch, apiPublicFetch } from "@/lib/api";

export interface HealthResponse {
  status: string;
  database: string;
}

export interface StatsResponse {
  patients: number;
  analyses: number;
  trials: number;
}

export interface OpenAIStatusResponse {
  status: string;
  openai: string;
  reason?: string | null;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await apiPublicFetch("/health");
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchStats(): Promise<StatsResponse> {
  const res = await apiFetch("/stats");
  if (!res.ok) throw new Error("Stats fetch failed");
  return res.json();
}

export async function fetchOpenAIStatus(): Promise<OpenAIStatusResponse> {
  const res = await apiFetch("/openai-status");
  if (!res.ok) throw new Error("OpenAI status check failed");
  return res.json();
}
