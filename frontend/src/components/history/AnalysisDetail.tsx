"use client";

import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft, Clock, MessageSquare, Target, Download } from "lucide-react";
import { type AnalysisDetail, type TrialDetail } from "@/services/history";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { TASK_LABELS, TASK_ICONS } from "@/constants/tasks";
import { useAnalysis } from "@/hooks/queries/use-history";
import { apiFetch } from "@/lib/api";

function AudioPlayer({ trialId }: { trialId: number }) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/trials/${trialId}/audio`);
        if (!res.ok || cancelled) {
          if (!cancelled) setError(true);
          return;
        }
        const blob = await res.blob();
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        setAudioUrl(url);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, [trialId]);

  if (loading) return <Loader2 className="h-4 w-4 animate-spin text-slate-400" />;
  if (error || !audioUrl) return null;

  return <audio controls src={audioUrl} className="w-full mt-2" preload="metadata" />;
}

function TrialCard({ trial }: { trial: TrialDetail }) {
  const m = trial.metrics ?? trial;
  const correctWords = (m.correct_words as string[] | null | undefined) ?? trial.correct_words;
  const sentenceCount = (m.sentence_count as number | null | undefined) ?? trial.sentence_count;
  const ttr = (m.ttr as number | null | undefined) ?? trial.ttr;
  const avgSentenceLength = (m.avg_sentence_length as number | null | undefined) ?? trial.avg_sentence_length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <span className="text-2xl">{TASK_ICONS[trial.task as keyof typeof TASK_ICONS] || "📋"}</span>
          {TASK_LABELS[trial.task as keyof typeof TASK_LABELS] || trial.task}
          {trial.points !== null && (
            <Badge variant="secondary" className="ml-auto">
              {trial.points} Punkte
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {trial.audio_duration_seconds !== null && (
            <div className="text-center p-3 bg-slate-50 rounded-lg">
              <Clock className="h-4 w-4 mx-auto mb-1 text-blue-600" />
              <div className="text-sm font-semibold">
                {Math.floor(trial.audio_duration_seconds / 60)}:
                {String(Math.floor(trial.audio_duration_seconds % 60)).padStart(2, "0")}
              </div>
              <div className="text-xs text-slate-500">Dauer</div>
            </div>
          )}
          {trial.total_word_count !== null && (
            <div className="text-center p-3 bg-slate-50 rounded-lg">
              <MessageSquare className="h-4 w-4 mx-auto mb-1 text-green-600" />
              <div className="text-sm font-semibold">{trial.total_word_count}</div>
              <div className="text-xs text-slate-500">Wörter</div>
            </div>
          )}
          {sentenceCount != null && (
            <div className="text-center p-3 bg-slate-50 rounded-lg">
              <Target className="h-4 w-4 mx-auto mb-1 text-orange-600" />
              <div className="text-sm font-semibold">{sentenceCount}</div>
              <div className="text-xs text-slate-500">Sätze</div>
            </div>
          )}
        </div>

        {correctWords && correctWords.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Korrekte Begriffe:</p>
            <div className="flex flex-wrap gap-1">
              {correctWords.map((word, idx) => (
                <Badge key={idx} variant="outline" className="text-xs">
                  {word}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {ttr != null && (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="text-center p-2 bg-blue-50 rounded">
              <div className="font-semibold">{ttr?.toFixed(2)}</div>
              <div className="text-xs text-slate-500">TTR</div>
            </div>
            {avgSentenceLength != null && (
              <div className="text-center p-2 bg-green-50 rounded">
                <div className="font-semibold">{avgSentenceLength?.toFixed(1)}</div>
                <div className="text-xs text-slate-500">Ø Satzlänge</div>
              </div>
            )}
          </div>
        )}

        {trial.transcript && (
          <div>
            <Separator className="my-3" />
            <p className="text-sm font-medium mb-1">Transkription:</p>
            <p className="text-sm text-slate-600 bg-slate-50 p-3 rounded-md italic">
              &ldquo;{trial.transcript}&rdquo;
            </p>
          </div>
        )}

        {trial.audio_uuid && (
          <div>
            <Separator className="my-3" />
            <p className="text-sm font-medium mb-1">Audioaufnahme:</p>
            <AudioPlayer trialId={trial.id} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function downloadJson(analysis: AnalysisDetail) {
  const currentDate = new Date().toISOString();
  const patientId = analysis.patient_id || "UNKNOWN";

  const trialsByTask: Record<string, object> = {};
  for (const t of analysis.trials) {
    trialsByTask[t.task] = {
      processedAt: t.processed_at,
      task: t.task,
      attemptId: t.attempt_id,
      transcript: t.transcript,
      metrics: t.metrics ?? {
        points: t.points,
        total_word_count: t.total_word_count,
        audio_duration_seconds: t.audio_duration_seconds,
        correct_words: t.correct_words,
        unrelated_words: t.unrelated_words,
        duplicate_count: t.duplicate_count,
        filler_word_count: t.filler_word_count,
        sentence_count: t.sentence_count,
        verb_count: t.verb_count,
        noun_count: t.noun_count,
        pronoun_count: t.pronoun_count,
        adverb_count: t.adverb_count,
        adjective_count: t.adjective_count,
        verb_ratio: t.verb_ratio,
        noun_ratio: t.noun_ratio,
        pronoun_ratio: t.pronoun_ratio,
        adverb_ratio: t.adverb_ratio,
        adjective_ratio: t.adjective_ratio,
        ttr: t.ttr,
        avg_sentence_length: t.avg_sentence_length,
      },
    };
  }

  const fullJsonOutput = {
    metaHeader: {
      workflow: "ParkSpeechApp",
      workflowVersion: "1.1.0",
      appVersion: "1.0.0",
      downloadDate: currentDate,
      patientID: patientId,
      datum: analysis.date || "",
      moca: analysis.moca_score ?? "",
      gruppe: analysis.group || "",
      notes: analysis.notes || "",
      sessionAnalysisId: analysis.session_analysis_id,
    },
    analysisResults: trialsByTask,
  };

  const jsonString = JSON.stringify(fullJsonOutput, null, 2);
  const blob = new Blob([jsonString], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;

  let fmtId = patientId.replace(/[^a-zA-Z0-9]/g, "");
  fmtId = fmtId.toUpperCase().startsWith("P") ? "P" + fmtId.substring(1) : "P" + fmtId;
  if (fmtId.length < 2) fmtId = "P000000";
  fmtId = fmtId.substring(0, 11);
  a.download = `${(analysis.date || currentDate).split("T")[0]}_${fmtId}_PSA.json`;

  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function AnalysisDetailView({ id }: { id: number }) {
  const { toast } = useToast();
  const { data: analysis, isPending: loading, error: queryError } = useAnalysis(id);
  const error = queryError?.message ?? null;

  const handleDownload = () => {
    if (!analysis) return;
    downloadJson(analysis);
    toast({ title: "Download gestartet", description: "Die JSON-Datei wird heruntergeladen." });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-red-600">
          {error || "Analyse nicht gefunden."}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <Link href="/history">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Zurück
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              Analyse #{analysis.id}
            </h1>
            <p className="text-slate-600">
              Patient: {analysis.patient_id || "–"} | Datum: {analysis.date || "–"} |
              Gruppe: {analysis.group || "–"}
              {analysis.moca_score !== null && ` | MoCA: ${analysis.moca_score}`}
            </p>
          </div>
        </div>

        <Button
          onClick={handleDownload}
          disabled={analysis.trials.length === 0}
          className="bg-emerald-600 hover:bg-emerald-700 text-white"
        >
          <Download className="mr-1.5 h-4 w-4" />
          JSON exportieren
        </Button>
      </div>

      {analysis.notes && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-slate-600">
              <strong>Notizen:</strong> {analysis.notes}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {analysis.trials.map((trial) => (
          <TrialCard key={trial.id} trial={trial} />
        ))}
      </div>

      {analysis.trials.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-slate-500">
            Keine Trials für diese Analyse vorhanden.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
