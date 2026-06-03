"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Key, Check, Trash2, Loader2, Eye, EyeOff, UserCircle, HardDrive, Mic,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";

const AUDIO_DEVICE_KEY = "speechscribe_audio_device_id";

interface UserInfo {
  username: string;
  is_active: boolean;
  is_admin: boolean;
  has_openai_key: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export default function SettingsPage() {
  const { toast } = useToast();

  // React Query for user info
  const { data: userInfo } = useQuery({
    queryKey: ["user-info"],
    queryFn: async () => {
      const res = await apiFetch("/user/me");
      return res.json() as Promise<UserInfo>;
    },
  });

  // React Query for openai-key status
  const { data: keyStatus } = useQuery({
    queryKey: ["openai-key-status"],
    queryFn: async () => {
      const res = await apiFetch("/user/openai-key/status");
      return res.json() as Promise<{ has_key: boolean }>;
    },
  });

  // Audio device selection
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");

  useEffect(() => {
    // Load saved device from localStorage
    const saved = localStorage.getItem(AUDIO_DEVICE_KEY);
    if (saved) setSelectedDeviceId(saved);

    // Enumerate audio input devices
    async function loadDevices() {
      try {
        // Need permission first to get device labels
        await navigator.mediaDevices.getUserMedia({ audio: true }).then(s => s.getTracks().forEach(t => t.stop()));
        const devices = await navigator.mediaDevices.enumerateDevices();
        setAudioDevices(devices.filter(d => d.kind === "audioinput"));
      } catch {
        // Permission denied or no devices
      }
    }
    loadDevices();
  }, []);

  // Test recording
  const [testRecording, setTestRecording] = useState(false);
  const [testAudioUrl, setTestAudioUrl] = useState<string | null>(null);
  const testRecorderRef = useRef<MediaRecorder | null>(null);
  const testChunksRef = useRef<Blob[]>([]);
  const testStreamRef = useRef<MediaStream | null>(null);
  const testCanvasRef = useRef<HTMLCanvasElement>(null);
  const testAnimRef = useRef<number>(0);
  const testAnalyserRef = useRef<AnalyserNode | null>(null);
  const testAudioCtxRef = useRef<AudioContext | null>(null);

  const stopTestRecording = useCallback(() => {
    testRecorderRef.current?.stop();
    cancelAnimationFrame(testAnimRef.current);
    testAnalyserRef.current = null;
    testAudioCtxRef.current?.close();
    testAudioCtxRef.current = null;
    testStreamRef.current?.getTracks().forEach(t => t.stop());
    testStreamRef.current = null;
    setTestRecording(false);
  }, []);

  const startTestRecording = async () => {
    // Clean up previous test
    if (testAudioUrl) {
      URL.revokeObjectURL(testAudioUrl);
      setTestAudioUrl(null);
    }

    try {
      const deviceId = selectedDeviceId || undefined;
      const constraints: MediaStreamConstraints = {
        audio: deviceId ? { deviceId: { exact: deviceId } } : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      testStreamRef.current = stream;

      // Waveform visualization
      const audioCtx = new AudioContext();
      testAudioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      testAnalyserRef.current = analyser;

      const canvas = testCanvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d")!;
        const bufLen = analyser.frequencyBinCount;
        const data = new Uint8Array(bufLen);

        const draw = () => {
          testAnimRef.current = requestAnimationFrame(draw);
          analyser.getByteTimeDomainData(data);
          const w = canvas.width, h = canvas.height;
          ctx.fillStyle = "#f8fafc";
          ctx.fillRect(0, 0, w, h);
          ctx.lineWidth = 2;
          ctx.strokeStyle = "#ef4444";
          ctx.beginPath();
          const slice = w / bufLen;
          let x = 0;
          for (let i = 0; i < bufLen; i++) {
            const y = (data[i] / 128.0) * h / 2;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            x += slice;
          }
          ctx.lineTo(w, h / 2);
          ctx.stroke();
        };
        draw();
      }

      // Recorder
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus" : "audio/webm",
      });
      testRecorderRef.current = recorder;
      testChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) testChunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(testChunksRef.current, { type: recorder.mimeType });
        if (blob.size > 0) {
          setTestAudioUrl(URL.createObjectURL(blob));
        }
      };

      recorder.start(1000);
      setTestRecording(true);

      // Auto-stop after 5 seconds
      setTimeout(() => {
        if (testRecorderRef.current?.state === "recording") {
          stopTestRecording();
        }
      }, 5000);
    } catch {
      toast({ title: "Mikrofon-Fehler", description: "Zugriff auf das Audiogeraet fehlgeschlagen.", variant: "destructive" });
    }
  };

  // Cleanup test audio URL on unmount
  useEffect(() => {
    return () => {
      if (testAudioUrl) URL.revokeObjectURL(testAudioUrl);
    };
  }, [testAudioUrl]);

  const handleDeviceChange = (deviceId: string) => {
    setSelectedDeviceId(deviceId);
    if (deviceId) {
      localStorage.setItem(AUDIO_DEVICE_KEY, deviceId);
    } else {
      localStorage.removeItem(AUDIO_DEVICE_KEY);
    }
    toast({ title: "Audiogeraet gespeichert", description: "Die Auswahl wird beim naechsten Aufnahmestart verwendet." });
  };

  // OpenAI Key management
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [hasKey, setHasKey] = useState<boolean | null>(null);
  const [savingKey, setSavingKey] = useState(false);
  const [deletingKey, setDeletingKey] = useState(false);

  useEffect(() => {
    if (keyStatus) setHasKey(keyStatus.has_key);
  }, [keyStatus]);

  const handleSaveKey = async () => {
    if (!apiKey.trim()) return;
    setSavingKey(true);
    try {
      const res = await apiFetch("/user/openai-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });
      if (!res.ok) throw new Error("Speichern fehlgeschlagen");
      setHasKey(true);
      setApiKey("");
      toast({ title: "API-Key gespeichert", description: "Der Key wurde verschluesselt in der Datenbank hinterlegt." });
    } catch {
      toast({ title: "Fehler beim Speichern", variant: "destructive" });
    } finally {
      setSavingKey(false);
    }
  };

  const handleDeleteKey = async () => {
    setDeletingKey(true);
    try {
      const res = await apiFetch("/user/openai-key", { method: "DELETE" });
      if (!res.ok) throw new Error("Loeschen fehlgeschlagen");
      setHasKey(false);
      toast({ title: "API-Key geloescht", description: "Der gespeicherte Key wurde entfernt." });
    } catch {
      toast({ title: "Fehler beim Loeschen", variant: "destructive" });
    } finally {
      setDeletingKey(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Einstellungen</h1>
        <p className="text-slate-600 mt-1">Persoenliche Einstellungen und API-Konfiguration.</p>
      </div>

      {/* Benutzer-Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <UserCircle className="h-5 w-5 text-sky-600" />
            Mein Profil
          </CardTitle>
        </CardHeader>
        <CardContent>
          {userInfo ? (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 text-sm">
              <div className="flex justify-between sm:block">
                <dt className="text-slate-500">Benutzername</dt>
                <dd className="font-medium text-slate-800">{userInfo.username}</dd>
              </div>
              <div className="flex justify-between sm:block">
                <dt className="text-slate-500">Rolle</dt>
                <dd className="font-medium">
                  {userInfo.is_admin ? (
                    <span className="text-violet-600">Admin</span>
                  ) : (
                    <span className="text-slate-600">Benutzer</span>
                  )}
                </dd>
              </div>
              <div className="flex justify-between sm:block">
                <dt className="text-slate-500">Status</dt>
                <dd className="font-medium">
                  {userInfo.is_active ? (
                    <span className="text-emerald-600">Aktiv</span>
                  ) : (
                    <span className="text-red-600">Inaktiv</span>
                  )}
                </dd>
              </div>
              <div className="flex justify-between sm:block">
                <dt className="text-slate-500">Erstellt am</dt>
                <dd className="font-medium text-slate-800">
                  {userInfo.created_at
                    ? new Date(userInfo.created_at).toLocaleDateString("de-DE", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "-"}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-slate-400">Wird geladen...</p>
          )}
        </CardContent>
      </Card>

      {/* Audio-Eingangsgeraet */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Mic className="h-5 w-5 text-blue-600" />
            Mikrofon / Audioeingang
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="audioDevice">Audiogeraet fuer Aufnahmen</Label>
            <select
              id="audioDevice"
              value={selectedDeviceId}
              onChange={(e) => handleDeviceChange(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-base h-12 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Standard (vom Browser gewaehlt)</option>
              {audioDevices.map((device) => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label || `Mikrofon (${device.deviceId.slice(0, 8)}...)`}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-400">
              Die Auswahl wird im Browser gespeichert und bleibt nach dem Neuladen erhalten.
            </p>
          </div>

          {/* Test recording */}
          <div className="border-t pt-3 space-y-2">
            <Label>Mikrofon testen</Label>
            <div className="flex gap-2">
              {testRecording ? (
                <Button
                  variant="destructive"
                  onClick={stopTestRecording}
                >
                  Stoppen
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={startTestRecording}
                >
                  Testaufnahme (max 5s)
                </Button>
              )}
            </div>
            <canvas
              ref={testCanvasRef}
              width={400}
              height={50}
              className={`w-full h-[50px] rounded-md border ${testRecording ? "border-red-300 bg-red-50/30" : "border-slate-200"}`}
            />
            {testAudioUrl && !testRecording && (
              <audio controls src={testAudioUrl} className="w-full h-8" />
            )}
          </div>
        </CardContent>
      </Card>

      {/* OpenAI API-Key */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Key className="h-5 w-5 text-amber-600" />
            OpenAI API-Key
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Status:</span>
            {hasKey === null ? (
              <span className="text-slate-400">Wird geladen...</span>
            ) : hasKey ? (
              <span className="flex items-center gap-1 text-emerald-600 font-medium">
                <Check className="h-4 w-4" /> Key hinterlegt (verschluesselt)
              </span>
            ) : (
              <span className="text-amber-600 font-medium">Kein Key gespeichert</span>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="apiKey">Neuen API-Key setzen</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="apiKey"
                  type={showKey ? "text" : "password"}
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  disabled={savingKey}
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-slate-400 hover:text-slate-600"
                >
                  {showKey ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
              <Button
                onClick={handleSaveKey}
                disabled={savingKey || !apiKey.trim()}
                className="bg-amber-600 hover:bg-amber-700 text-white"
              >
                {savingKey ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : null}
                Speichern
              </Button>
            </div>
            <p className="text-xs text-slate-400">
              Der Key wird mit Fernet verschluesselt in der User-Datenbank gespeichert.
              Falls kein Key hinterlegt ist, wird der Server-Fallback (.env) verwendet.
            </p>
          </div>

          {hasKey && (
            <Button
              onClick={handleDeleteKey}
              disabled={deletingKey}
              variant="outline"
              size="sm"
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              {deletingKey ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-1.5 h-4 w-4" />
              )}
              Gespeicherten Key loeschen
            </Button>
          )}
        </CardContent>
      </Card>

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <HardDrive className="h-5 w-5 text-slate-500" />
            System-Info
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 text-sm">
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Frontend</dt>
              <dd className="font-medium text-slate-800">Next.js (React)</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Backend</dt>
              <dd className="font-medium text-slate-800">FastAPI (Python)</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Datenbank</dt>
              <dd className="font-medium text-slate-800">SQLite</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">Transkription</dt>
              <dd className="font-medium text-slate-800">OpenAI Whisper</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">NLP</dt>
              <dd className="font-medium text-slate-800">spaCy (de_core_news_sm)</dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-slate-500">API-URL</dt>
              <dd className="font-medium text-slate-800 font-mono text-xs">
                {typeof window !== "undefined"
                  ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
                  : "-"}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
