/**
 * Type definitions for audio processing and analysis
 */

import * as React from 'react';

// ── Metrics ──────────────────────────────────────────────

export interface AnalysisMetrics {
  // Common
  points?: number;
  total_word_count?: number;
  audio_duration_seconds?: number;

  // Veggie task
  correct_words?: string[];
  unrelated_words?: number;
  unrelated_words_list?: string[];
  duplicate_count?: number;

  // Saying task
  filler_word_count?: number;

  // Picture task
  pic_points?: number;
  sentence_count?: number;
  verb_count?: number;
  noun_count?: number;
  pronoun_count?: number;
  adverb_count?: number;
  adjective_count?: number;
  verb_ratio?: number;
  noun_ratio?: number;
  pronoun_ratio?: number;
  adverb_ratio?: number;
  adjective_ratio?: number;
  ttr?: number;
  avg_sentence_length?: number;
  filler_counter?: number;

  [key: string]: unknown;
}

export const defaultMetrics: AnalysisMetrics = {
  points: undefined,
  total_word_count: undefined,
  audio_duration_seconds: undefined,
  correct_words: [],
  unrelated_words: undefined,
  duplicate_count: undefined,
  filler_word_count: undefined,
  pic_points: undefined,
  sentence_count: undefined,
  verb_count: undefined,
  noun_count: undefined,
  pronoun_count: undefined,
  adverb_count: undefined,
  adjective_count: undefined,
  verb_ratio: undefined,
  noun_ratio: undefined,
  pronoun_ratio: undefined,
  adverb_ratio: undefined,
  adjective_ratio: undefined,
  ttr: undefined,
  avg_sentence_length: undefined,
  filler_counter: undefined,
};

// ── API Responses ────────────────────────────────────────

export interface FastAPIAnalysisResponse {
  processedAt: string;
  task: string;
  attemptId: string;
  transcript: string;
  metrics: AnalysisMetrics;
  error?: string;
  dbId?: number;
}

export interface BackendFullAnalysisResponse {
  processedAt: string;
  task: string;
  attemptId: string;
  transcript: string;
  metrics: AnalysisMetrics;
  db_id?: number;
  error?: string;
  detail?: unknown;
}

// ── Results / Visualization ──────────────────────────────

export type TaskType = 'veggie' | 'saying' | 'picture';

export type PerformanceLevel = 'excellent' | 'good' | 'fair' | 'needs_improvement';

export interface TestResult {
  taskType: TaskType;
  taskName: string;
  points: number;
  maxPoints: number;
  duration: number;
  wordCount: number;
  transcription?: string;
  metrics: AnalysisMetrics;
  performance: PerformanceLevel;
}

export interface AnalysisResponse {
  taskType: TaskType;
  metrics: AnalysisMetrics;
  points: number;
  maxPoints: number;
  duration: number;
  wordCount: number;
  transcription?: string;
}

// ── Component Props ──────────────────────────────────────

export interface AudioProcessorProps {
  taskTitle: string;
  taskDescription: string | React.ReactNode;
  taskType: TaskType;
  onAnalysisComplete?: (taskType: string, result: FastAPIAnalysisResponse | null) => void;
  patientId?: string;
  testDate?: string;
  group?: string;
  birthDate?: string;
  gender?: string;
  mocaScore?: string;
  notes?: string;
  sessionId?: string;
  sessionAnalysisId?: string;
  saveToDatabase?: boolean;
}

export interface AudioProcessorHandle {
  process: (overrideSessionAnalysisId?: string) => Promise<void>;
  hasFile: () => boolean;
  getTaskType: () => string;
  reset?: () => void;
}

export interface ResultsVisualizationProps {
  results: TestResult[];
  patientName?: string;
  testDate?: string;
  overallScore?: number;
  recommendations?: string[];
}
