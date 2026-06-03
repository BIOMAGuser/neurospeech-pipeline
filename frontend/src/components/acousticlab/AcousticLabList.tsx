"use client";

import { useState } from "react";
import { CheckCircle2, Circle, Loader2, Play, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { useComputeAcoustic } from "@/hooks/queries/use-acousticlab";
import type { AcousticTrialRow, Confidence, Gender } from "@/types/acousticlab";

import AcousticLabDetail from "./AcousticLabDetail";
import RowAudioButton from "./RowAudioButton";

interface Props {
  trials: AcousticTrialRow[];
}

const GENDER_LABEL: Record<Gender, string> = {
  m: "♂",
  f: "♀",
  d: "⚧",
  unknown: "?",
};

function ageFromBand(band: string, birthDate: string | null, testDate: string | null): string {
  if (band !== "unknown") return band;
  if (birthDate && testDate) {
    try {
      const bd = new Date(birthDate);
      const td = new Date(testDate);
      const years = Math.floor((td.getTime() - bd.getTime()) / (365.25 * 24 * 3600 * 1000));
      if (years > 0 && years < 130) return `${years}j`;
    } catch {
      // fallthrough
    }
  }
  return "—";
}

const TASK_LABEL: Record<string, string> = {
  veggie: "Gemüse",
  saying: "Sprichwort",
  picture: "Bildbeschreibung",
  voicesample: "Stimmprobe",
};

function taskLabel(task: string): string {
  return TASK_LABEL[task] ?? task;
}

function shortDate(iso: string | null): string | null {
  if (!iso) return null;
  // backend returns ISO date or datetime; we only need the day part
  const head = iso.slice(0, 10);
  // de-DE compact: 2017-09-26 -> 26.09.17
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(head);
  if (!m) return head;
  return `${m[3]}.${m[2]}.${m[1].slice(2)}`;
}

function groupBadge(group: AcousticTrialRow["group"]) {
  if (!group) return <span className="text-slate-400">—</span>;
  const variant: "secondary" | "destructive" | "default" =
    group === "Parkinson" ? "destructive" : group === "Kontrolle" ? "default" : "secondary";
  return (
    <Badge variant={variant} className="text-[10px] uppercase">
      {group}
    </Badge>
  );
}

export default function AcousticLabList({ trials }: Props) {
  const { toast } = useToast();
  const compute = useComputeAcoustic();
  const [selectedTrial, setSelectedTrial] = useState<number | null>(null);
  const [busyTrial, setBusyTrial] = useState<number | null>(null);

  const handleCompute = async (trialId: number) => {
    setBusyTrial(trialId);
    try {
      await compute.mutateAsync({ trialId });
      toast({ title: "Acoustic-Features berechnet", description: `Trial ${trialId}` });
    } catch (e) {
      toast({
        title: "Fehler",
        description: (e as Error).message,
        variant: "destructive",
      });
    } finally {
      setBusyTrial(null);
    }
  };

  if (trials.length === 0) {
    return (
      <div className="text-center py-16 text-slate-400 border rounded-lg bg-slate-50">
        Keine Trials mit Audio gefunden.
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="border rounded-lg bg-white overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[1fr_60px_80px_100px_70px_70px_180px] md:grid-cols-[1fr_60px_80px_120px_80px_80px_140px_180px] gap-2 px-4 py-2 text-xs font-semibold text-slate-500 uppercase border-b bg-slate-50">
          <span>Patient · Task</span>
          <span className="text-center">Sex</span>
          <span className="text-center">Alter</span>
          <span>Gruppe</span>
          <span className="text-right">Audio</span>
          <span className="text-center">Status</span>
          <span className="text-center hidden md:block">Score</span>
          <span className="text-right">Aktion</span>
        </div>

        {/* Rows */}
        {trials.map((t) => {
          const isBusy = busyTrial === t.trial_id;
          const ageDisplay = ageFromBand(t.age_band, t.birth_date, t.test_date);
          return (
            <div
              key={t.trial_id}
              className="grid grid-cols-[1fr_60px_80px_100px_70px_70px_180px] md:grid-cols-[1fr_60px_80px_120px_80px_80px_140px_180px] gap-2 px-4 py-2.5 items-center border-b last:border-b-0 hover:bg-slate-50 cursor-pointer"
              onClick={() => setSelectedTrial(t.trial_id)}
            >
              <div className="min-w-0">
                <div className="font-medium truncate flex items-center gap-1.5">
                  <span className="truncate">{t.patient_cd ?? "?"}</span>
                  {t.patient_cd?.startsWith("DEMO-") && (
                    <Badge variant="outline" className="text-[9px] px-1 py-0 shrink-0">
                      DEMO
                    </Badge>
                  )}
                </div>
                <div className="text-xs text-slate-500 truncate">
                  Trial #{t.trial_id} · {taskLabel(t.task)}
                  {shortDate(t.test_date) && (
                    <span className="ml-2 text-slate-400">· {shortDate(t.test_date)}</span>
                  )}
                </div>
              </div>
              <div className="text-center">{GENDER_LABEL[t.gender] ?? "?"}</div>
              <div className="text-center text-sm">{ageDisplay}</div>
              <div className="truncate">{groupBadge(t.group)}</div>
              <div className="text-right text-xs text-slate-500 tabular-nums">
                {t.audio_duration_s != null ? `${t.audio_duration_s.toFixed(1)}s` : "—"}
              </div>
              <div className="flex justify-center">
                {t.acoustic_computed ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                ) : (
                  <Circle className="h-5 w-5 text-slate-300" />
                )}
              </div>
              <div className="hidden md:flex justify-center">
                {t.acoustic_computed ? (
                  <ScoreBadge score={t.score} confidence={t.confidence} />
                ) : (
                  <span className="text-slate-300 text-xs">—</span>
                )}
              </div>
              <div className="flex justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant={t.acoustic_computed ? "outline" : "default"}
                      disabled={isBusy}
                      onClick={() => handleCompute(t.trial_id)}
                      className="gap-1.5"
                    >
                      {isBusy ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : t.acoustic_computed ? (
                        <RefreshCw className="h-3.5 w-3.5" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                      {isBusy ? "Läuft" : t.acoustic_computed ? "Neu" : "Start"}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {t.acoustic_computed
                      ? "Akustik-Features neu berechnen (überschreibt vorhandene Werte)"
                      : "Akustik-Features für diesen Trial berechnen"}
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <RowAudioButton trialId={t.trial_id} />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    Audio-Aufnahme abspielen
                    {t.audio_duration_s != null
                      ? ` (${t.audio_duration_s.toFixed(1)}s)`
                      : ""}
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          );
        })}
      </div>

      <AcousticLabDetail
        trialId={selectedTrial}
        onClose={() => setSelectedTrial(null)}
      />
    </TooltipProvider>
  );
}

// Score badge — values come pre-computed in the trial row from /acoustic/trials,
// so the list doesn't fire N per-row score requests.
function ScoreBadge({
  score,
  confidence,
}: {
  score: number | null;
  confidence: Confidence | null;
}) {
  if (score == null) {
    return (
      <Badge variant="secondary" className="text-[10px]">
        {confidence === "low" ? "low conf" : "n/a"}
      </Badge>
    );
  }
  const variant: "default" | "destructive" | "secondary" =
    score >= 0.7 ? "destructive" : score <= 0.3 ? "default" : "secondary";
  return (
    <Badge variant={variant} className="tabular-nums">
      {score.toFixed(2)}
    </Badge>
  );
}
