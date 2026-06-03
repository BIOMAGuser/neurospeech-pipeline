// src/hooks/use-results-processing.ts
'use client';

import { TestResult, AnalysisResponse, TaskType } from '@/types/audio';
import { TASK_MAP, TASKS } from '@/constants/tasks';

export const useResultsProcessing = () => {
  const processAnalysisToTestResult = (
    analysis: AnalysisResponse,
    taskName: string
  ): TestResult => {
    const performance = getPerformanceLevel(analysis.points, analysis.maxPoints, analysis.taskType);

    return {
      taskType: analysis.taskType,
      taskName,
      points: analysis.points,
      maxPoints: analysis.maxPoints,
      duration: analysis.duration,
      wordCount: analysis.wordCount,
      transcription: analysis.transcription,
      metrics: analysis.metrics,
      performance
    };
  };

  const getPerformanceLevel = (points: number, maxPoints: number, taskType?: TaskType): TestResult['performance'] => {
    const config = taskType ? TASK_MAP[taskType] : undefined;

    // Use task-specific absolute thresholds if defined
    if (config?.performanceThresholds) {
      const t = config.performanceThresholds;
      if (points >= t.excellent) return 'excellent';
      if (points >= t.good) return 'good';
      if (points >= t.fair) return 'fair';
      return 'needs_improvement';
    }

    // Default: percentage-based evaluation
    const percentage = (points / maxPoints) * 100;
    if (percentage >= 90) return 'excellent';
    if (percentage >= 75) return 'good';
    if (percentage >= 60) return 'fair';
    return 'needs_improvement';
  };

  const generateRecommendations = (results: TestResult[]): string[] => {
    const recommendations: string[] = [];

    results.forEach(result => {
      if (result.taskType === 'veggie') {
        if (result.points >= 15) {
          recommendations.push('Gemüseaufgabe: Hervorragende Wortfindung! Sehr gut gemacht.');
        } else if (result.points >= 10) {
          recommendations.push('Gemüseaufgabe: Gute Leistung! Sie haben viele richtige Begriffe gefunden.');
        } else if (result.points >= 6) {
          recommendations.push('Gemüseaufgabe: Schöner Anfang! Mit etwas Übung werden Sie noch mehr Begriffe finden.');
        } else {
          recommendations.push('Gemüseaufgabe: Nehmen Sie sich Zeit - jeder Begriff zählt. Versuchen Sie verschiedene Gemüsesorten zu durchdenken.');
        }
      }

      if (result.taskType === 'picture') {
        const percentage = (result.points / result.maxPoints) * 100;
        if (percentage >= 85) {
          recommendations.push('Bildbeschreibung: Sehr detaillierte und präzise Beschreibung!');
        } else if (percentage >= 70) {
          recommendations.push('Bildbeschreibung: Gute Beobachtungsgabe! Sie haben wichtige Details erkannt.');
        } else {
          recommendations.push('Bildbeschreibung: Versuchen Sie, alle Personen und Aktivitäten im Bild zu beschreiben.');
        }
      }

      if (result.taskType === 'saying') {
        if (result.points > 0) {
          recommendations.push('Sprichwort: Ausgezeichnet! Sie kennen dieses Sprichwort sehr gut.');
        } else {
          recommendations.push('Sprichwort: Sprichwörter können manchmal knifflig sein. Lassen Sie sich Zeit zum Nachdenken.');
        }
      }
    });

    return Array.from(new Set(recommendations));
  };

  const getTaskDisplayName = (taskType: string): string => {
    const config = TASK_MAP[taskType as TaskType];
    return config?.label || taskType;
  };

  return {
    processAnalysisToTestResult,
    generateRecommendations,
    getTaskDisplayName,
    getPerformanceLevel
  };
};

export default useResultsProcessing;
