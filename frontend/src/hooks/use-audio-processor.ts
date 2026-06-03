/**
 * Custom hook for audio processing state and logic
 */

import { useState, useCallback, type ChangeEvent } from 'react';
import { useToast } from '@/hooks/use-toast';
import { usePatient } from '@/hooks/use-patient';
import { getAudioDurationWithFallback, validateAudioFile, formatAudioDuration } from '@/lib/audio-utils';
import { AudioAnalysisService, type AnalysisRequestData } from '@/services/audio-analysis';
import { FastAPIAnalysisResponse, TaskType } from '@/types/audio';

interface UseAudioProcessorProps {
  taskType: TaskType;
  taskTitle: string;
  onAnalysisComplete?: (taskType: string, result: FastAPIAnalysisResponse | null) => void;
  sessionId?: string;
  sessionAnalysisId?: string;
}

export const useAudioProcessor = (props: UseAudioProcessorProps) => {
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<FastAPIAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number | null>(null);

  const { toast } = useToast();
  const { patient } = usePatient();

  const applySelectedFile = useCallback(async (selectedFile: File | null) => {
    setError(null);
    setAnalysisResult(null);
    setAudioDuration(null);

    if (selectedFile) {
      const validation = validateAudioFile(selectedFile);
      if (!validation.isValid) {
        toast({
          title: 'Ungültige Datei',
          description: validation.error!,
          variant: 'destructive',
        });
        setFile(null);
        props.onAnalysisComplete?.(props.taskType, null);
        return;
      }

      setFile(selectedFile);

      try {
        const duration = await getAudioDurationWithFallback(selectedFile);
        setAudioDuration(duration);

        toast({
          title: 'Datei geladen',
          description: `${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB, ${duration.toFixed(1)}s)`,
          variant: 'default',
        });

        if (duration < 1 && selectedFile.size > 100000) {
          toast({
            title: 'Info',
            description: `Audiodauer: ${duration.toFixed(1)}s (geschätzt basierend auf Dateigröße)`,
            variant: 'default',
          });
        }
      } catch {
        toast({
          title: 'Warnung',
          description: 'Audiodauer konnte nicht ermittelt werden, aber die Datei kann trotzdem verarbeitet werden.',
          variant: 'default',
        });
      }
    } else {
      setFile(null);
    }

    props.onAnalysisComplete?.(props.taskType, null);
  }, [props.taskType, props.onAnalysisComplete, toast]);

  const handleFileChange = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    await applySelectedFile(selectedFile ?? null);
    if (!selectedFile && event.target) event.target.value = '';
  }, [applySelectedFile]);

  const processAudio = useCallback(async (overrideSessionAnalysisId?: string) => {
    if (!file) {
      toast({
        title: 'Keine Datei ausgewählt',
        description: `Bitte wählen Sie eine Datei für ${props.taskTitle}.`,
        variant: 'destructive',
      });
      return;
    }

    if (audioDuration === null) {
      toast({
        title: 'Audio-Dauer unbekannt',
        description: 'Die Dauer der Audiodatei konnte nicht ermittelt werden oder wird noch geladen.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    setError(null);

    const requestData: AnalysisRequestData = {
      file,
      taskType: props.taskType,
      attemptId: `attempt_${crypto.randomUUID()}`,
      audioDuration,
      patientId: patient.patientId,
      testDate: patient.testDate,
      group: patient.group,
      birthDate: patient.birthDate,
      gender: patient.gender,
      mocaScore: patient.mocaScore,
      notes: patient.notes,
      sessionId: props.sessionId,
      sessionAnalysisId: overrideSessionAnalysisId || props.sessionAnalysisId,
      saveToDatabase: patient.saveToDatabase,
    };

    try {
      const result = await AudioAnalysisService.analyzeAudio(requestData);

      setAnalysisResult(result);
      props.onAnalysisComplete?.(props.taskType, result);

      toast({
        title: `Verarbeitung abgeschlossen: ${props.taskTitle}`,
        description: 'Audio erfolgreich verarbeitet.',
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unbekannter Fehler';

      setError(`Verarbeitung fehlgeschlagen: ${msg}`);
      setAnalysisResult(null);
      props.onAnalysisComplete?.(props.taskType, null);

      toast({
        title: `Verarbeitungsfehler: ${props.taskTitle}`,
        description: msg,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [
    file,
    audioDuration,
    props.taskType,
    props.taskTitle,
    props.onAnalysisComplete,
    props.sessionId,
    props.sessionAnalysisId,
    patient,
    toast,
  ]);

  const hasFile = useCallback(() => !!file, [file]);

  const getFileInfo = useCallback(() => {
    if (!file) return null;
    return {
      name: file.name,
      duration: audioDuration ? formatAudioDuration(audioDuration) : null,
    };
  }, [file, audioDuration]);

  const reset = useCallback(() => {
    setFile(null);
    setAnalysisResult(null);
    setError(null);
    setAudioDuration(null);
  }, []);

  return {
    file,
    isLoading,
    analysisResult,
    error,
    audioDuration,
    handleFileChange,
    setAudioFile: applySelectedFile,
    processAudio,
    hasFile,
    getFileInfo,
    reset,
    taskType: props.taskType,
  };
};
