/**
 * Audio Analysis Service
 * Handles API communication for audio processing and analysis
 */

import { apiFetch } from '@/lib/api';
import {
  BackendFullAnalysisResponse,
  FastAPIAnalysisResponse,
  AnalysisMetrics,
  TaskType,
  defaultMetrics,
} from '@/types/audio';

export interface AnalysisRequestData {
  file: File;
  taskType: TaskType;
  attemptId: string;
  audioDuration: number;
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

export class AudioAnalysisService {
  static buildFormData(data: AnalysisRequestData): FormData {
    const formData = new FormData();
    
    // Required fields
    formData.append('audio', data.file);
    formData.append('taskType', data.taskType);
    formData.append('attemptId', data.attemptId);
    formData.append('duration_seconds', data.audioDuration.toString());

    // Optional fields
    if (data.patientId) formData.append('patient_id', data.patientId);
    if (data.testDate) formData.append('test_date', data.testDate);
    if (data.group) formData.append('group', data.group);
    if (data.birthDate) formData.append('birth_date', data.birthDate);
    if (data.gender) formData.append('gender', data.gender);
    if (data.mocaScore) formData.append('moca_score', data.mocaScore);
    if (data.notes) formData.append('notes', data.notes);
    if (data.sessionId) formData.append('session_id', data.sessionId);
    if (data.sessionAnalysisId) formData.append('session_analysis_id', data.sessionAnalysisId);
    
    // Database save option (default true if not specified)
    formData.append('save_to_database', data.saveToDatabase !== false ? 'true' : 'false');

    return formData;
  }

  static async processErrorResponse(response: Response): Promise<string> {
    let processedErrorMsg = `Server antwortete mit Status ${response.status}`;
    const responseContentType = response.headers.get("content-type");

    if (responseContentType && responseContentType.includes("application/json")) {
      try {
        const errorJson = await response.json();
        if (Array.isArray(errorJson.detail)) {
          processedErrorMsg = errorJson.detail.map((err: any) => {
            const loc = err.loc && Array.isArray(err.loc) ? err.loc.join(' -> ') : (err.loc ? String(err.loc) : 'field');
            return `${loc}: ${err.msg}`;
          }).join('; ');
        } else if (typeof errorJson.detail === 'string') {
          processedErrorMsg = errorJson.detail;
        } else if (typeof errorJson.error === 'string') {
          processedErrorMsg = errorJson.error;
        } else if (errorJson.detail) {
          processedErrorMsg = JSON.stringify(errorJson.detail);
        }
      } catch (jsonError) {
        console.error("Fehler beim Parsen der JSON-Fehlerantwort:", jsonError);
        const errorText = await response.text().catch(() => "Nicht lesbare Fehlerantwort");
        processedErrorMsg = `Fehler beim Verarbeiten der Serverantwort. Status: ${response.status}. Antwort: ${errorText.substring(0, 200)}`;
      }
    } else {
      try {
        const errorText = await response.text();
        if (errorText && errorText.length < 1000) {
          processedErrorMsg = errorText;
        } else if (errorText) {
          processedErrorMsg = `Serverfehler (Status ${response.status}) - Details siehe Server-Log.`;
        }
      } catch (textError) {
        console.error("Fehler beim Lesen der Text-Fehlerantwort:", textError);
      }
    }

    if (response.status === 404) {
      const endpointPath = new URL(response.url).pathname;
      const serverOrigin = new URL(response.url).origin;
      return `Endpunkt nicht gefunden (404): Der Pfad '${endpointPath}' wurde auf dem Server '${serverOrigin}' nicht gefunden. Servermeldung: ${processedErrorMsg}`;
    }

    return processedErrorMsg;
  }

  static processMetrics(backendMetrics: AnalysisMetrics, taskType: TaskType, audioDuration: number): AnalysisMetrics {
    return {
      ...defaultMetrics,
      ...(backendMetrics || {}),
      audio_duration_seconds: audioDuration,
    };
  }

  static async analyzeAudio(data: AnalysisRequestData): Promise<FastAPIAnalysisResponse> {
    const formData = this.buildFormData(data);

    const response = await apiFetch('/analyze', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorMessage = await this.processErrorResponse(response);
      throw new Error(errorMessage);
    }

    const backendData: BackendFullAnalysisResponse = await response.json();

    if (backendData.error && typeof backendData.error === 'string') {
      throw new Error(backendData.error);
    }

    const combinedMetrics = this.processMetrics(backendData.metrics, data.taskType, data.audioDuration);

    const frontendResponse: FastAPIAnalysisResponse = {
      processedAt: backendData.processedAt,
      task: backendData.task,
      attemptId: backendData.attemptId,
      transcript: backendData.transcript,
      metrics: combinedMetrics,
      dbId: backendData.db_id,
    };

    return frontendResponse;
  }
} 