"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart3, Download, RotateCcw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { usePatient } from "@/hooks/use-patient";
import { useResultsProcessing } from "@/hooks/use-results-processing";
import ResultsVisualization from "@/components/ResultsVisualization";
import { FastAPIAnalysisResponse, TaskType, TestResult } from "@/types/audio";
import { TASK_MAP } from "@/constants/tasks";

interface AnalysisSectionProps {
  isGlobalLoading: boolean;
  canStartAnalysis: boolean;
  allTaskResults: Record<TaskType, FastAPIAnalysisResponse | null>;
  onStartAnalysis: () => void;
  onResetAll: () => void;
}

export default function AnalysisSection({
  isGlobalLoading,
  canStartAnalysis,
  allTaskResults,
  onStartAnalysis,
  onResetAll,
}: AnalysisSectionProps) {
  const { toast } = useToast();
  const { patient, updateField } = usePatient();
  const { processAnalysisToTestResult, generateRecommendations, getTaskDisplayName } =
    useResultsProcessing();

  const hasResults = Object.values(allTaskResults).some(Boolean);

  const getVisualResults = (): TestResult[] => {
    const results: TestResult[] = [];
    Object.entries(allTaskResults).forEach(([taskType, analysis]) => {
      if (analysis?.metrics) {
        const config = TASK_MAP[taskType as TaskType];
        const points = (analysis.metrics[config.pointsKey] as number) ?? analysis.metrics.points ?? 0;

        results.push(
          processAnalysisToTestResult(
            {
              taskType: taskType as TaskType,
              metrics: analysis.metrics,
              points,
              maxPoints: config.maxPoints,
              duration: analysis.metrics.audio_duration_seconds || 0,
              wordCount: analysis.metrics.total_word_count || 0,
              transcription: analysis.transcript,
            },
            getTaskDisplayName(taskType)
          )
        );
      }
    });
    return results;
  };

  const handleDownloadAllResults = () => {
    const { patientId, testDate } = patient;
    if (!patientId.trim() || !testDate.trim()) {
      toast({
        title: "Fehlende Eingabe",
        description: "Bitte geben Sie Patienten-ID und Sitzungsdatum ein.",
        variant: "destructive",
      });
      return;
    }
    if (!hasResults) {
      toast({
        title: "Keine Ergebnisse",
        description: "Noch keine Ergebnisse zum Herunterladen vorhanden.",
        variant: "destructive",
      });
      return;
    }

    const currentDate = new Date().toISOString();
    const { birthDate, gender, mocaScore, group } = patient;
    const fullJsonOutput = {
      metaHeader: {
        workflow: "ParkSpeechApp",
        workflowVersion: "1.1.0",
        appVersion: "1.0.0",
        downloadDate: currentDate,
        patientID: patientId.trim(),
        datum: testDate.trim(),
        geburtsdatum: birthDate.trim(),
        geschlecht: gender.trim(),
        moca: mocaScore.trim(),
        gruppe: group.trim(),
      },
      analysisResults: allTaskResults,
    };

    const jsonString = JSON.stringify(fullJsonOutput, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    let fmtId = patientId.trim().replace(/[^a-zA-Z0-9]/g, "");
    fmtId = fmtId.toUpperCase().startsWith("P") ? "P" + fmtId.substring(1) : "P" + fmtId;
    if (fmtId.length < 2) fmtId = "P000000";
    fmtId = fmtId.substring(0, 11);
    a.download = `${currentDate.split("T")[0]}_${fmtId}_PSA.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast({ title: "Download gestartet", description: "Die JSON-Datei wird heruntergeladen." });
  };

  return (
    <div className="space-y-6">
      {/* Save to DB checkbox */}
      <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
        <input
          type="checkbox"
          id="saveToDatabase"
          checked={patient.saveToDatabase}
          onChange={(e) => updateField("saveToDatabase", e.target.checked)}
          className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
        />
        <label htmlFor="saveToDatabase" className="text-sm font-medium text-gray-700 cursor-pointer">
          Ergebnisse in Datenbank speichern
        </label>
        <span className="text-xs text-gray-500 ml-2">
          (Deaktivieren für Tests ohne permanente Speicherung)
        </span>
      </div>

      {/* Results visualization — shown automatically when results exist */}
      {hasResults && (
        <div className="w-full">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Ergebnisübersicht</h2>
          <ResultsVisualization
            results={getVisualResults()}
            patientName={patient.patientId}
            testDate={patient.testDate}
            recommendations={generateRecommendations(getVisualResults())}
          />
        </div>
      )}

      {!hasResults && (
        <Card className="p-6 text-center">
          <CardContent>
            <p className="text-gray-600">
              Noch keine Testergebnisse vorhanden.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Action buttons: JSON export + reset */}
      {hasResults && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Button
            onClick={handleDownloadAllResults}
            className="bg-emerald-600 hover:bg-emerald-700 text-white py-3"
            disabled={!patient.patientId.trim() || !patient.testDate.trim()}
          >
            <Download className="mr-2 h-4 w-4" />
            Ergebnisse herunterladen (JSON)
          </Button>

          <Button
            onClick={onResetAll}
            variant="outline"
            className="py-3"
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Neue Messung starten
          </Button>
        </div>
      )}
    </div>
  );
}
