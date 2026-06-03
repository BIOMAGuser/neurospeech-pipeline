/**
 * AudioProcessor Component - Refactored to use PatientContext
 */

'use client';

import React, { forwardRef, useImperativeHandle, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, MessageSquareText } from 'lucide-react';
import { useAudioProcessor } from '@/hooks/use-audio-processor';
import MetricsDisplay from './MetricsDisplay';
import AudioRecorder from './AudioRecorder';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  FastAPIAnalysisResponse,
  AudioProcessorHandle,
  TaskType,
} from '@/types/audio';
import { TASK_ICONS, TASK_MAP } from '@/constants/tasks';

// Re-export types for backward compatibility
export type {
  FastAPIAnalysisResponse,
  AudioProcessorHandle,
  TaskType,
} from '@/types/audio';

export interface AudioProcessorProps {
  taskTitle: string;
  taskDescription: string | React.ReactNode;
  taskType: TaskType;
  onAnalysisComplete?: (taskType: string, result: FastAPIAnalysisResponse | null) => void;
  sessionId?: string;
  sessionAnalysisId?: string;
}

export const AudioProcessor = forwardRef<AudioProcessorHandle, AudioProcessorProps>(({
  taskTitle,
  taskDescription,
  taskType,
  onAnalysisComplete,
  sessionId,
  sessionAnalysisId,
}, ref) => {

  const {
    isLoading,
    analysisResult,
    error,
    handleFileChange,
    setAudioFile,
    processAudio,
    hasFile,
    getFileInfo,
    reset,
  } = useAudioProcessor({
    taskType,
    taskTitle,
    onAnalysisComplete,
    sessionId,
    sessionAnalysisId,
  });

  useImperativeHandle(ref, () => ({
    process: (overrideSessionAnalysisId?: string) => processAudio(overrideSessionAnalysisId),
    hasFile,
    getTaskType: () => taskType,
    reset,
  }));

  const [tab, setTab] = useState('upload');
  const fileInfo = getFileInfo();

  return (
    <Card className="shadow-lg w-full flex flex-col h-full border border-slate-200 transition-all duration-200 hover:shadow-xl hover:border-blue-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl font-semibold text-slate-800">
          <span role="img" aria-label={taskType} style={{ fontSize: '1.5em' }}>
            {TASK_ICONS[taskType]}
          </span>
          {taskTitle}
          {hasFile() && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full ml-auto">
              ✓ Datei bereit
            </span>
          )}
        </CardTitle>
        <CardDescription className="text-slate-600 h-20 overflow-hidden">
          {taskDescription}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5 flex-grow flex flex-col">
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="upload">Datei hochladen</TabsTrigger>
            <TabsTrigger value="record">Aufnehmen</TabsTrigger>
          </TabsList>
          <TabsContent value="upload">
            <div className="grid w-full items-center gap-3 mt-2">
              <Label htmlFor={`audio-file-${taskType}`} className="font-medium text-slate-700">
                Audiodatei
              </Label>
              <Input
                id={`audio-file-${taskType}`}
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                disabled={isLoading}
                className="file:text-blue-600 file:font-semibold hover:file:cursor-pointer border-slate-300 focus:border-blue-500 focus:ring-blue-500"
              />
              {fileInfo && (
                <p className="text-sm text-slate-500 mt-1">
                  Ausgewählt: {fileInfo.name} {fileInfo.duration && `(${fileInfo.duration})`}
                </p>
              )}
            </div>
          </TabsContent>
          <TabsContent value="record">
            <div className="mt-2">
              <AudioRecorder onRecordingComplete={setAudioFile} disabled={isLoading} taskType={taskType} timerSeconds={TASK_MAP[taskType]?.timerSeconds} />
              {fileInfo && (
                <p className="text-sm text-slate-500 mt-1">
                  Aufnahme: {fileInfo.name} {fileInfo.duration && `(${fileInfo.duration})`}
                </p>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {isLoading && (
          <div className="flex items-center justify-center mt-4">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Verarbeite...
          </div>
        )}

        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertTitle className="font-semibold">Fehler</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {analysisResult && !error && (
          <div className="space-y-6 mt-4 flex-grow">
            <Card className="shadow-inner bg-white">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg text-slate-700">
                  <MessageSquareText className="text-blue-600" />
                  Transkription
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  readOnly
                  value={analysisResult.transcript}
                  className="min-h-[120px] resize-none bg-slate-50 border-slate-200 p-3 rounded-md"
                  aria-label="Transkriptionsergebnis"
                />
              </CardContent>
            </Card>

            <MetricsDisplay metrics={analysisResult.metrics} />
          </div>
        )}
      </CardContent>
    </Card>
  );
});

AudioProcessor.displayName = 'AudioProcessor';
