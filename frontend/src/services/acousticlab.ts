import { apiFetch } from "@/lib/api";
import type {
  AcousticFeatures,
  AcousticTrialRow,
  CohortSummary,
  TrialScore,
} from "@/types/acousticlab";

export async function fetchAcousticTrials(): Promise<AcousticTrialRow[]> {
  const res = await apiFetch("/acoustic/trials");
  if (!res.ok) throw new Error(`Trials laden fehlgeschlagen (${res.status})`);
  return res.json();
}

export async function computeAcoustic(
  trialId: number,
  signal?: AbortSignal,
): Promise<AcousticFeatures> {
  const res = await apiFetch(`/trials/${trialId}/acoustic`, {
    method: "POST",
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Acoustic-Berechnung fehlgeschlagen (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchTrialScore(trialId: number): Promise<TrialScore | null> {
  const res = await apiFetch(`/trials/${trialId}/acoustic/score`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Score laden fehlgeschlagen (${res.status})`);
  return res.json();
}

export async function fetchCohort(): Promise<CohortSummary> {
  const res = await apiFetch("/acoustic/cohort");
  if (!res.ok) throw new Error(`Kohorte laden fehlgeschlagen (${res.status})`);
  return res.json();
}

export interface SamplesStatus {
  downloaded: boolean;
  extracted: boolean;
  zip_path: string;
  extracted_dir: string;
  zip_size_mb: number | null;
  n_imported: number | null;
}

export async function fetchSamplesStatus(): Promise<SamplesStatus> {
  const res = await apiFetch("/acoustic/samples/status");
  if (!res.ok) throw new Error(`Status laden fehlgeschlagen (${res.status})`);
  return res.json();
}

export interface SampleDeleteResult {
  patients_deleted: number;
  mp3_deleted: number;
}

export async function deleteSamples(): Promise<SampleDeleteResult> {
  const res = await apiFetch("/acoustic/samples", { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Demo-Löschen fehlgeschlagen (${res.status}): ${text}`);
  }
  return res.json();
}

// Each event from POST /acoustic/samples/load (one JSON per line).
export type SampleLoadEvent =
  | { phase: "download"; status: "starting" | "cached" | "done"; bytes?: number; url?: string }
  | { phase: "download"; status: "progress"; downloaded_mb: number; total_mb: number | null; pct: number | null }
  | { phase: "extract"; status: "starting" | "done"; wav_count?: number }
  | { phase: "import"; status?: "starting"; wav_count?: number; current?: number; total?: number; kind?: "imported" | "skipped"; patient_cd?: string }
  | { phase: "done"; imported: number; skipped: number; by_group: Record<string, number>; trial_ids: number[] }
  | { phase: "error"; message: string; type: string };

/**
 * POST /acoustic/samples/load and consume the ndjson stream.
 * Calls onEvent for every line. Resolves with the final "done" event
 * (or rejects on "error").
 */
export async function streamLoadSamples(
  onEvent: (evt: SampleLoadEvent) => void,
  signal?: AbortSignal,
): Promise<Extract<SampleLoadEvent, { phase: "done" }>> {
  const res = await apiFetch("/acoustic/samples/load", { method: "POST", signal });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(`Sample-Load fehlgeschlagen (${res.status}): ${text}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let final: Extract<SampleLoadEvent, { phase: "done" }> | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl = buf.indexOf("\n");
    while (nl !== -1) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (line) {
        try {
          const evt = JSON.parse(line) as SampleLoadEvent;
          onEvent(evt);
          if (evt.phase === "done") final = evt;
          if (evt.phase === "error") throw new Error(evt.message);
        } catch (e) {
          // skip malformed lines but surface unexpected errors
          if (e instanceof Error && e.message.startsWith("Unexpected")) {
            // JSON parse error — ignore
          } else {
            throw e;
          }
        }
      }
      nl = buf.indexOf("\n");
    }
  }
  if (!final) throw new Error("Stream beendete ohne 'done'-Event");
  return final;
}
