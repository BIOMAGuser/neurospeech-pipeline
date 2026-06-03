// Types for the AcousticLab tab.

export type Gender = "m" | "f" | "d" | "unknown";
export type Group = "Kontrolle" | "Parkinson" | "Sonstiges" | null;
export type Confidence = "low" | "med" | "high";

export interface AcousticTrialRow {
  trial_id: number;
  task: string;
  audio_uuid: string;
  audio_duration_s: number | null;
  patient_cd: string | null;
  gender: Gender;
  age_band: string;
  birth_date: string | null;
  test_date: string | null;
  group: Group;
  encounter_num: number;
  patient_num: number;
  acoustic_computed: boolean;
  // Inlined by the backend so the list view doesn't need a per-row /score call.
  score: number | null;
  confidence: Confidence | null;
}

export interface PerFeatureScore {
  value: number;
  percentile_control: number | null;
  percentile_pd: number | null;
  n_control: number;
  n_pd: number;
}

export interface TrialScore {
  trial_id: number;
  task: string;
  patient_cd: string | null;
  gender: Gender;
  age_band: string;
  group: Group;
  confidence: Confidence;
  score: number | null;
  log_likelihood_ratio: number | null;
  n_features_used: number;
  per_feature: Record<string, PerFeatureScore>;
}

export interface CohortCell {
  gender: Gender;
  age_band: string;
  group: "Kontrolle" | "Parkinson";
  n_observations: number;
  sample_features: Record<string, { mu: number; n: number }>;
}

export interface CohortSummary {
  cells: CohortCell[];
  total_cells: number;
}

export interface AcousticFeatures {
  observation_id: number;
  task: string;
  audio_uuid: string;
  audio_duration_s: number | null;
  computation_ms: number;
  feature_count: number;
  features: Record<string, number | null>;
}
