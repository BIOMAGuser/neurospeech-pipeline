"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

interface AudioRecorderProps {
  onRecordingComplete: (file: File) => void;
  disabled?: boolean;
  taskType?: 'veggie' | 'saying' | 'picture';
  timerSeconds?: number | null;
}

function AudioWaveform({ stream }: { stream: MediaStream }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      analyser.getByteTimeDomainData(dataArray);

      const w = canvas.width;
      const h = canvas.height;

      ctx.fillStyle = "rgb(248, 250, 252)"; // slate-50
      ctx.fillRect(0, 0, w, h);

      ctx.lineWidth = 2;
      ctx.strokeStyle = "rgb(239, 68, 68)"; // red-500
      ctx.beginPath();

      const sliceWidth = w / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * h) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }

      ctx.lineTo(w, h / 2);
      ctx.stroke();
    };

    draw();

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      source.disconnect();
      audioCtx.close();
    };
  }, [stream]);

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={60}
      className="w-full h-[60px] rounded-md border border-red-200"
      role="img"
      aria-label="Audio-Wellenform"
    />
  );
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({ onRecordingComplete, disabled, taskType, timerSeconds }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [remainingTime, setRemainingTime] = useState<number | null>(null);
  const [activeStream, setActiveStream] = useState<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    setActiveStream(null);

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRemainingTime(null);
  }, []);

  const startRecording = async () => {
    if (disabled) return;
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Ihr Browser unterstützt keine Audioaufnahme");
      }

      const savedDeviceId = localStorage.getItem("speechscribe_audio_device_id");
      const audioConstraints: MediaTrackConstraints = savedDeviceId
        ? { deviceId: { exact: savedDeviceId } }
        : true;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });

      let mimeType = 'audio/webm';
      let fileExtension = 'webm';

      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
        fileExtension = 'webm';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
        fileExtension = 'mp4';
      } else if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
        fileExtension = 'wav';
      } else if (MediaRecorder.isTypeSupported('audio/mpeg')) {
        mimeType = 'audio/mpeg';
        fileExtension = 'mp3';
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const fileName = `recording_${Date.now()}.${fileExtension}`;
        const file = new File([blob], fileName, { type: mimeType });

        const url = URL.createObjectURL(blob);
        setAudioUrl(url);

        onRecordingComplete(file);

        stream.getTracks().forEach((track) => track.stop());

        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setRemainingTime(null);

        toast({
          title: "Aufnahme abgeschlossen",
          description: `Audiodatei erstellt: ${fileName} (${(file.size / 1024).toFixed(1)} KB)`,
          variant: "default"
        });
      };

      mediaRecorder.start(1000); // collect data every second
      setIsRecording(true);
      setActiveStream(stream);

      if (timerSeconds && timerSeconds > 0) {
        setRemainingTime(timerSeconds);
        let timeLeft = timerSeconds;

        timerRef.current = setInterval(() => {
          timeLeft -= 1;
          setRemainingTime(timeLeft);

          if (timeLeft <= 0) {
            stopRecording();
          }
        }, 1000);
      }

      toast({
        title: "Aufnahme gestartet",
        description: timerSeconds ? `Format: ${mimeType} - Zeitlimit: ${timerSeconds}s` : `Format: ${mimeType}`,
        variant: "default"
      });

    } catch (err) {
      console.error("Error starting recording", err);
      let errorMessage = "Fehler beim Starten der Aufnahme";

      if (err instanceof Error) {
        if (err.name === "NotAllowedError") {
          errorMessage = "Mikrofonzugriff verweigert. Bitte erlauben Sie den Zugriff auf das Mikrofon in Ihrem Browser.";
        } else if (err.name === "NotFoundError") {
          errorMessage = "Kein Mikrofon gefunden. Bitte überprüfen Sie, ob ein Mikrofon angeschlossen ist.";
        } else if (err.name === "NotSupportedError") {
          errorMessage = "Audioaufnahme wird von Ihrem Browser nicht unterstützt.";
        } else if (err.name === "NotReadableError") {
          errorMessage = "Mikrofon wird bereits von einer anderen Anwendung verwendet.";
        } else {
          errorMessage = err.message;
        }
      }

      toast({
        title: "Aufnahme-Fehler",
        description: errorMessage,
        variant: "destructive"
      });
    }
  };

  // Cleanup only on unmount — refs always hold current values
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      if (timerRef.current) clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Revoke old audio URL when it changes
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  return (
    <div className="space-y-4">
      <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-md">
        <p><strong>Hinweis:</strong> Für die Audioaufnahme benötigt Ihr Browser Zugriff auf das Mikrofon.</p>
        <p>Falls Sie eine Fehlermeldung erhalten, überprüfen Sie bitte die Mikrofon-Berechtigung.</p>
      </div>

      <div className="flex gap-2">
        {isRecording ? (
          <Button variant="destructive" size="lg" onClick={stopRecording} className="flex-1" aria-label="Aufnahme stoppen">
            🔴 Aufnahme stoppen {remainingTime !== null && `(${remainingTime}s)`}
          </Button>
        ) : (
          <Button size="lg" onClick={startRecording} disabled={disabled} className="flex-1" aria-label="Aufnahme starten">
            🎤 Aufnahme starten {timerSeconds && timerSeconds > 0 && `(max. ${timerSeconds}s)`}
          </Button>
        )}
      </div>

      {isRecording && activeStream && (
        <AudioWaveform stream={activeStream} />
      )}

      {audioUrl && !isRecording && (
        <div className="space-y-2">
          <p className="text-sm text-slate-600">Aufnahme bereit:</p>
          <audio controls src={audioUrl} className="w-full" />
        </div>
      )}
    </div>
  );
};

export default AudioRecorder;
