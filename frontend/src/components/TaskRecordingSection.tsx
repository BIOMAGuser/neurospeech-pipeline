"use client";

import { useState } from "react";
import {
  AudioProcessor,
  type AudioProcessorHandle,
  type FastAPIAnalysisResponse,
} from "@/components/AudioProcessor";
import { Button } from "@/components/ui/button";
import { Eye } from "lucide-react";
import CookieTheftPicture from "@/components/CookieTheftPicture";
import { TaskType } from "@/types/audio";

interface Task {
  id: TaskType;
  title: string;
  description: string;
  ref: React.RefObject<AudioProcessorHandle>;
}

interface TaskRecordingSectionProps {
  tasks: Task[];
  sessionId: string;
  sessionAnalysisId: string;
  onAnalysisComplete: (taskType: string, result: FastAPIAnalysisResponse | null) => void;
}

export default function TaskRecordingSection({
  tasks,
  sessionId,
  sessionAnalysisId,
  onAnalysisComplete,
}: TaskRecordingSectionProps) {
  const [showCookieTheftPicture, setShowCookieTheftPicture] = useState(false);

  const getTaskDescription = (task: Task): string | React.ReactNode => {
    if (task.id === "picture") {
      return (
        <div className="space-y-2">
          <p>{task.description}</p>
          <Button
            onClick={() => setShowCookieTheftPicture(true)}
            variant="outline"
            size="sm"
            className="text-blue-600 border-blue-600 hover:bg-blue-50"
          >
            <Eye className="w-4 h-4 mr-2" />
            Bild anzeigen
          </Button>
        </div>
      );
    }
    return task.description;
  };

  return (
    <>
      <p className="text-sm text-gray-600 mb-4">
        Laden Sie Audioaufnahmen für die jeweiligen Aufgaben hoch, um Transkriptionen und detaillierte Analysen zu erhalten.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 w-full">
        {tasks.map((task) => (
          <AudioProcessor
            key={task.id}
            ref={task.ref}
            taskTitle={task.title}
            taskDescription={getTaskDescription(task)}
            taskType={task.id}
            onAnalysisComplete={onAnalysisComplete}
            sessionId={sessionId}
            sessionAnalysisId={sessionAnalysisId}
          />
        ))}
      </div>

      {showCookieTheftPicture && (
        <CookieTheftPicture
          isVisible={showCookieTheftPicture}
          onClose={() => setShowCookieTheftPicture(false)}
        />
      )}
    </>
  );
}
