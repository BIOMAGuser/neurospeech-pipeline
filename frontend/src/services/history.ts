import { apiFetch } from "@/lib/api";

export interface PatientListItem {
  id: number;
  patient_id: string;
  gender: string | null;
  birth_date: string | null;
  created_at: string | null;
  created_by: string | null;
  analysis_count: number;
  export_status: "full" | "partial" | "none";
}

export interface TrialDetail {
  id: number;
  task: string;
  processed_at: string | null;
  attempt_id: string;
  transcript: string | null;
  audio_duration_seconds: number | null;
  audio_uuid: string | null;
  total_word_count: number | null;
  points: number | null;
  metrics?: Record<string, unknown>; // Unified metrics from metrics_json
  // Legacy fields (kept for old data compatibility)
  correct_words?: string[] | null;
  unrelated_words?: number | null;
  duplicate_count?: number | null;
  filler_word_count?: number | null;
  sentence_count?: number | null;
  verb_count?: number | null;
  noun_count?: number | null;
  pronoun_count?: number | null;
  adverb_count?: number | null;
  adjective_count?: number | null;
  verb_ratio?: number | null;
  noun_ratio?: number | null;
  pronoun_ratio?: number | null;
  adverb_ratio?: number | null;
  adjective_ratio?: number | null;
  ttr?: number | null;
  avg_sentence_length?: number | null;
}

export interface AnalysisDetail {
  id: number;
  patient_id: string | null;
  date: string | null;
  moca_score: number | null;
  group: string | null;
  notes: string | null;
  session_analysis_id: string;
  created_at: string | null;
  trials: TrialDetail[];
}

export interface PatientAnalysisListItem {
  id: number;
  date: string | null;
  moca_score: number | null;
  group: string | null;
  session_analysis_id: string;
  exported_at: string | null;
  created_at: string | null;
  trial_count: number;
}

export async function fetchPatients(): Promise<PatientListItem[]> {
  const res = await apiFetch("/patients");
  if (!res.ok) throw new Error("Failed to fetch patients");
  return res.json();
}

export async function fetchAnalysis(id: number): Promise<AnalysisDetail> {
  const res = await apiFetch(`/analyses/${id}`);
  if (!res.ok) throw new Error("Failed to fetch analysis");
  return res.json();
}

export async function deleteAnalysis(id: number): Promise<void> {
  const res = await apiFetch(`/analyses/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete analysis");
}

export async function deletePatient(id: number): Promise<void> {
  const res = await apiFetch(`/patients/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete patient");
}

export async function exportPatient(id: number): Promise<unknown> {
  const res = await apiFetch(`/patients/${id}/export`);
  if (!res.ok) throw new Error("Failed to export patient");
  return res.json();
}

export async function exportAnalysis(id: number): Promise<unknown> {
  const res = await apiFetch(`/analyses/${id}/export`);
  if (!res.ok) throw new Error("Failed to export analysis");
  return res.json();
}

export interface ImportSummary {
  patients_created: number;
  analyses_created: number;
  analyses_skipped: number;
  trials_created: number;
}

export async function importPatientJson(data: unknown): Promise<ImportSummary> {
  const res = await apiFetch("/import/patient", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Import fehlgeschlagen" }));
    throw new Error(err.detail || "Import fehlgeschlagen");
  }
  return res.json();
}

export async function importAnalysisJson(data: unknown): Promise<ImportSummary> {
  const res = await apiFetch("/import/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Import fehlgeschlagen" }));
    throw new Error(err.detail || "Import fehlgeschlagen");
  }
  return res.json();
}

export async function fetchPatientAnalyses(
  patientId: number
): Promise<PatientAnalysisListItem[]> {
  const res = await apiFetch(`/patients/${patientId}/analyses`);
  if (!res.ok) throw new Error("Failed to fetch patient analyses");
  return res.json();
}
