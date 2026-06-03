/* eslint-disable @typescript-eslint/no-explicit-any */
// src/components/MetricsDisplay.tsx
'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChartBig, Clock } from 'lucide-react';
import { AnalysisMetrics } from '@/types/audio';

const labelMap: Record<string, string> = {
  points: "Punkte",
  correct_words: "Korrekte Wörter", 
  unrelated_words: "Falsche Wörter", 
  unrelated_words_list: "Falsche Wörter (Details)",
  duplicate_count: "Doppelte Wörter", 
  total_word_count: "Gesamtwortzahl",
  audio_duration_seconds: "Zeit (Sekunden)", // Label for audio duration
  verb_ratio: "Verhältnis Verben",
  noun_ratio: "Verhältnis Nomen",
  filler_word_count: "Füllwörter", 
  pic_points: "Punkte (Bild)", 
  sentence_count: "Anzahl Sätze",
  verb_count: "Anzahl Verben",
  noun_count: "Anzahl Nomen",
  pronoun_count: "Anzahl Pronomen",
  adverb_count: "Anzahl Adverbien",
  adjective_count: "Anzahl Adjektive",
  pronoun_ratio: "Verhältnis Pronomen",
  adverb_ratio: "Verhältnis Adverbien",
  adjective_ratio: "Verhältnis Adjektive",
  ttr: "Type-Token-Ratio (TTR)", 
  avg_sentence_length: "Durchschn. Satzlänge",
  filler_counter: "Füllwörter (Bild)" 
};

function formatKey(key: string): string {
  if (labelMap[key]) {
    return labelMap[key];
  }
  return key.replaceAll("_", " ").replace(/^\w/, w => w.toUpperCase());
}

const formatValue = (key: string, value: any): string => {
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "Keine";
    }
    return value.join(", ");
  }
  if (typeof value === "number") {
    const integerKeys = [
      'points', 'total_word_count', 'filler_counter', 'filler_word_count', 'pic_points',
      'unrelated_words', 'duplicate_count', 'sentence_count', 'verb_count', 'noun_count',
      'pronoun_count', 'adverb_count', 'adjective_count'
    ];
    if (integerKeys.includes(key)) {
      return value.toFixed(0);
    }
    return value.toString(); 
  }
  return value?.toString() ?? 'N/V';
};

interface MetricsDisplayProps {
  metrics: AnalysisMetrics;
}

const MetricsDisplay: React.FC<MetricsDisplayProps> = ({ metrics }) => {
  const validMetricEntries = metrics 
    ? Object.entries(metrics).filter(([key, value]) => {
        if (value === undefined || value === null || value === "NaN" || value === "None") {
          return false;
        }
        if (Array.isArray(value) && value.length === 0) {
          return false;
        }
        // Only show unrelated_words_list if there are actually wrong words
        if (key === 'unrelated_words_list') {
          return Array.isArray(value) && value.length > 0;
        }
        // Ensure audio_duration_seconds is displayed even if it's 0
        if (key === 'audio_duration_seconds' && value === 0) {
            return true;
        }
        return true;
      })
    : [];

  if (!metrics || validMetricEntries.length === 0) {
    return <p className="text-sm text-slate-500 p-3">Keine Analysemetriken verfügbar.</p>;
  }
  
  // Optional: Add audio_duration_seconds to a preferred order if you want it at a specific position
  // For simplicity, not re-implementing full preferredOrder logic here, but you could add it.

  return (
    <Card className="shadow-inner">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <BarChartBig className="text-blue-600" />
          Analysemetriken
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {validMetricEntries.map(([key, value]) => (
          <div key={key} className={`py-1 px-3 flex justify-between rounded-md bg-slate-50 hover:bg-slate-100 text-sm ${
            key === 'unrelated_words_list' ? 'border-l-4 border-red-400 bg-red-50' : ''
          }`}>
            <span className="font-medium text-slate-700">{formatKey(key)}:</span>
            <span className={`font-mono whitespace-normal break-words text-right ${
              key === 'unrelated_words_list' ? 'text-red-600 font-semibold' : 'text-blue-600'
            }`}>
              {formatValue(key, value)}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

export default MetricsDisplay;
