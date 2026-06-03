"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Loader2, ChevronLeft, ChevronRight, FlaskConical, AlertTriangle } from "lucide-react";
import { useOpenAIStatus } from "@/hooks/queries/use-dashboard";
import { PatientContext, usePatientState } from "@/hooks/use-patient";
import PatientInfoForm from "@/components/PatientInfoForm";
import TaskRecordingSection from "@/components/TaskRecordingSection";
import AnalysisSection from "@/components/AnalysisSection";
import WizardStepper from "@/components/measurement/WizardStepper";
import { type FastAPIAnalysisResponse, type AudioProcessorHandle } from "@/types/audio";
import { TaskType } from "@/types/audio";
import { TASKS } from "@/constants/tasks";

interface Task {
  id: TaskType;
  title: string;
  description: string;
  ref: React.RefObject<AudioProcessorHandle>;
}

const initialTasksState = Object.fromEntries(
  TASKS.map((t) => [t.id, null])
) as Record<TaskType, FastAPIAnalysisResponse | null>;

export default function MeasurementWizard() {
  const { toast } = useToast();
  const patientState = usePatientState();
  const { data: openai, isPending: openaiPending } = useOpenAIStatus();
  const openaiOk = openai ? openai.status === "ok" : null;
  const [step, setStep] = useState(1);

  const [sessionId, setSessionId] = useState("");
  const [sessionAnalysisId, setSessionAnalysisId] = useState("");
  const [allTaskResults, setAllTaskResults] =
    useState<Record<TaskType, FastAPIAnalysisResponse | null>>(initialTasksState);
  const [isGlobalLoading, setIsGlobalLoading] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState({ current: 0, total: 0 });
  const [analysisDone, setAnalysisDone] = useState(false);
  // Track whether any task has a file (re-checked via ref polling)
  const [hasAnyFile, setHasAnyFile] = useState(false);

  const taskRefs = useRef(
    new Map<TaskType, React.RefObject<AudioProcessorHandle>>(
      TASKS.map((cfg) => [cfg.id, { current: null } as React.RefObject<AudioProcessorHandle>])
    )
  );

  const tasks: Task[] = TASKS.map((cfg) => ({
    id: cfg.id,
    title: cfg.label,
    description: cfg.description,
    ref: taskRefs.current.get(cfg.id)!,
  }));

  const checkHasAnyFile = useCallback(() => {
    const has = tasks.some((t) => t.ref.current?.hasFile());
    setHasAnyFile(has);
    return has;
  }, []);

  const handleTaskAnalysisComplete = (
    taskType: string,
    result: FastAPIAnalysisResponse | null
  ) => {
    if (taskType in initialTasksState) {
      setAllTaskResults((prev) => ({ ...prev, [taskType as TaskType]: result }));
    }
    // Re-check file state whenever a task reports back
    checkHasAnyFile();
  };

  const handleSprachanalyse = async () => {
    const tasksWithFiles = tasks.filter((t) => t.ref.current?.hasFile());
    if (tasksWithFiles.length === 0) {
      toast({
        title: "Keine Dateien ausgewählt",
        description: "Bitte wählen Sie mindestens eine Audiodatei für die Analyse aus.",
      });
      return;
    }

    // Move to step 3 immediately
    setStep(3);
    setAnalysisDone(false);

    const newSessionAnalysisId = `analysis_${crypto.randomUUID()}`;
    setSessionId(`session_${crypto.randomUUID()}`);
    setSessionAnalysisId(newSessionAnalysisId);
    setIsGlobalLoading(true);
    setAnalysisProgress({ current: 0, total: tasksWithFiles.length });

    for (let i = 0; i < tasksWithFiles.length; i++) {
      setAnalysisProgress({ current: i + 1, total: tasksWithFiles.length });
      try {
        await tasksWithFiles[i].ref.current!.process(newSessionAnalysisId);
      } catch {
        toast({
          title: `Fehler bei ${tasksWithFiles[i].title}`,
          description: "Die Verarbeitung ist fehlgeschlagen.",
          variant: "destructive",
        });
      }
    }

    toast({
      title: "Alle Analysen abgeschlossen",
      description: "Die Ergebnisse werden angezeigt.",
    });
    setIsGlobalLoading(false);
    setAnalysisDone(true);
  };

  const handleResetAll = () => {
    patientState.reset();
    setAllTaskResults(initialTasksState);
    setAnalysisDone(false);
    setAnalysisProgress({ current: 0, total: 0 });
    setHasAnyFile(false);
    setSessionId("");
    setSessionAnalysisId("");
    tasks.forEach((t) => t.ref.current?.reset?.());
    setStep(1);
  };

  return (
    <PatientContext.Provider value={patientState}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Neue Messung</h1>
          <p className="text-slate-600 mt-1">
            Durchlaufen Sie die drei Schritte zur Sprachanalyse.
          </p>
        </div>

        <WizardStepper currentStep={step} />

        {/* All steps stay mounted for ref preservation */}
        <div className={step === 1 ? "" : "hidden"}>
          <PatientInfoForm />
        </div>

        <div className={step === 2 ? "" : "hidden"}>
          {openaiOk === false && (
            <div className="flex items-center gap-3 p-4 mb-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <div className="text-sm">
                <span className="font-medium">Kein gültiger OpenAI API-Key.</span>{" "}
                Bitte unter{" "}
                <a href="/settings" className="underline font-medium">Einstellungen</a>{" "}
                hinterlegen, um eine Analyse starten zu können.
              </div>
            </div>
          )}
          <TaskRecordingSection
            tasks={tasks}
            sessionId={sessionId}
            sessionAnalysisId={sessionAnalysisId}
            onAnalysisComplete={handleTaskAnalysisComplete}
          />
        </div>

        <div className={step === 3 ? "" : "hidden"}>
          {isGlobalLoading ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-4">
              <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
              <p className="text-lg font-medium text-slate-700">
                Auswertung läuft... {analysisProgress.current}/{analysisProgress.total}
              </p>
              <p className="text-sm text-slate-500">
                Bitte warten Sie, bis alle Aufgaben verarbeitet sind.
              </p>
              <div className="w-64 bg-slate-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${(analysisProgress.current / analysisProgress.total) * 100}%` }}
                />
              </div>
            </div>
          ) : analysisDone ? (
            <AnalysisSection
              isGlobalLoading={false}
              canStartAnalysis={false}
              allTaskResults={allTaskResults}
              onStartAnalysis={() => {}}
              onResetAll={handleResetAll}
            />
          ) : null}
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between pt-6 border-t border-slate-200">
          <Button
            variant="outline"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1 || isGlobalLoading}
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            Zurück
          </Button>

          {step === 1 && (
            <Button
              size="lg"
              onClick={() => setStep(2)}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Weiter
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          )}

          {step === 2 && (
            <Button
              size="lg"
              onClick={handleSprachanalyse}
              onMouseEnter={checkHasAnyFile}
              onFocus={checkHasAnyFile}
              disabled={!hasAnyFile || isGlobalLoading || openaiOk === false}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <FlaskConical className="mr-1.5 h-4 w-4" />
              Auswertung starten
            </Button>
          )}
        </div>
      </div>
    </PatientContext.Provider>
  );
}
