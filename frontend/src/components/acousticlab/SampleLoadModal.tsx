"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Download, Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import {
  computeAcoustic,
  streamLoadSamples,
  type SampleLoadEvent,
} from "@/services/acousticlab";

interface Props {
  onClose: () => void;
}

type Phase = "download" | "extract" | "import" | "compute" | "done" | "error";

interface State {
  phase: Phase;
  message: string;
  pct: number;
  detail?: string;
}

const INITIAL: State = {
  phase: "download",
  message: "Verbindung zu Zenodo …",
  pct: 0,
};

export default function SampleLoadModal({ onClose }: Props) {
  const { toast } = useToast();
  const qc = useQueryClient();
  const [state, setState] = useState<State>(INITIAL);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [importedCount, setImportedCount] = useState({ imported: 0, skipped: 0 });
  const [computedCount, setComputedCount] = useState({ done: 0, total: 0, errors: 0 });
  const abortRef = useRef(new AbortController());

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const final = await streamLoadSamples((evt: SampleLoadEvent) => {
          if (cancelled) return;
          if (evt.phase === "error") {
            setErrorMsg(evt.message);
            setState((s) => ({ ...s, phase: "error", message: evt.message, pct: 100 }));
            return;
          }
          if (evt.phase === "download") {
            if (evt.status === "starting") {
              setState({ phase: "download", message: "ZIP wird geladen …", pct: 0 });
            } else if (evt.status === "cached") {
              setState({
                phase: "download", message: "ZIP gefunden im Cache",
                pct: 100,
              });
            } else if (evt.status === "progress") {
              const pct = evt.pct ?? 0;
              setState({
                phase: "download",
                message: `Download ${evt.downloaded_mb.toFixed(1)} / ${
                  evt.total_mb?.toFixed(1) ?? "?"
                } MB`,
                pct,
              });
            } else if (evt.status === "done") {
              setState((s) => ({ ...s, message: "Download fertig", pct: 100 }));
            }
          } else if (evt.phase === "extract") {
            setState({
              phase: "extract",
              message: evt.status === "done"
                ? `Entpackt — ${evt.wav_count} WAV-Dateien gefunden`
                : "Entpacke ZIP …",
              pct: evt.status === "done" ? 100 : 50,
            });
          } else if (evt.phase === "import") {
            if (evt.status === "starting") {
              setState({
                phase: "import",
                message: `Import startet (${evt.wav_count} Dateien) …`,
                pct: 0,
              });
            } else if (evt.current != null && evt.total != null) {
              setState({
                phase: "import",
                message: `Patient ${evt.current}/${evt.total} (${evt.kind}): ${evt.patient_cd ?? ""}`,
                pct: Math.round(100 * evt.current / evt.total),
              });
            }
          } else if (evt.phase === "done") {
            setImportedCount({ imported: evt.imported, skipped: evt.skipped });
          }
        }, abortRef.current.signal);

        if (cancelled) return;

        // Phase 4: compute acoustic for all newly-imported trials
        const trialIds = final.trial_ids;
        setComputedCount({ done: 0, total: trialIds.length, errors: 0 });
        setState({
          phase: "compute",
          message: trialIds.length === 0
            ? "Keine neuen Trials zum Berechnen"
            : `Acoustic-Berechnung 0/${trialIds.length}`,
          pct: 0,
        });

        let done = 0;
        let errors = 0;
        for (const tid of trialIds) {
          if (cancelled || abortRef.current.signal.aborted) break;
          try {
            await computeAcoustic(tid, abortRef.current.signal);
          } catch {
            errors += 1;
          }
          done += 1;
          setComputedCount({ done, total: trialIds.length, errors });
          setState({
            phase: "compute",
            message: `Acoustic-Berechnung ${done}/${trialIds.length}`,
            pct: trialIds.length > 0 ? Math.round(100 * done / trialIds.length) : 100,
          });
        }

        if (cancelled) return;

        setState({
          phase: "done",
          message: "Fertig",
          pct: 100,
          detail: `${final.imported} neu (${final.by_group.Kontrolle ?? 0} HC, ${
            final.by_group.Parkinson ?? 0
          } PD), ${final.skipped} bereits vorhanden, ${done} berechnet${
            errors ? `, ${errors} Fehler` : ""
          }`,
        });

        qc.invalidateQueries({ queryKey: ["acoustic-trials"] });
        qc.invalidateQueries({ queryKey: ["acoustic-cohort"] });

        toast({
          title: "MDVR-KCL Demo geladen",
          description: `${final.imported} neue Demo-Patienten · ${done} Acoustic-Berechnungen`,
        });
      } catch (e) {
        if (!cancelled) {
          const msg = (e as Error).message;
          setErrorMsg(msg);
          setState((s) => ({ ...s, phase: "error", message: msg, pct: 100 }));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isRunning = state.phase !== "done" && state.phase !== "error";
  const handleCancel = () => {
    abortRef.current.abort();
  };

  return (
    <Dialog open onOpenChange={(o) => !o && !isRunning && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {state.phase === "done" ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            ) : (
              <Download className="h-5 w-5" />
            )}
            MDVR-KCL Demo-Daten
          </DialogTitle>
          <DialogDescription>
            Lädt 37 Sprachaufnahmen (16 Parkinson + 21 Kontrolle) aus dem
            öffentlichen MDVR-KCL-Datensatz von Zenodo (CC-BY-4.0, ~600 MB).
            Demografie wird deterministisch synthetisiert. Patienten werden mit
            Präfix <code className="text-xs bg-slate-100 px-1 rounded">DEMO-MDVR-</code> markiert.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 mt-2">
          <PhaseStep
            label="1. Download"
            active={state.phase === "download"}
            done={["extract", "import", "compute", "done"].includes(state.phase)}
            error={state.phase === "error" && state.message.toLowerCase().includes("download")}
          />
          <PhaseStep
            label="2. Entpacken"
            active={state.phase === "extract"}
            done={["import", "compute", "done"].includes(state.phase)}
          />
          <PhaseStep
            label="3. In DB importieren"
            active={state.phase === "import"}
            done={["compute", "done"].includes(state.phase)}
          />
          <PhaseStep
            label="4. Acoustic-Features berechnen"
            active={state.phase === "compute"}
            done={state.phase === "done"}
          />

          <div className="pt-2">
            <Progress value={state.pct} />
            <div className="text-sm text-slate-600 mt-1.5 tabular-nums">
              {state.message}
              {state.detail && <div className="mt-1 text-xs text-slate-500">{state.detail}</div>}
            </div>
            {errorMsg && (
              <div className="text-sm text-red-600 mt-2 break-words">
                Fehler: {errorMsg}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          {isRunning ? (
            <Button variant="outline" onClick={handleCancel} className="gap-1.5">
              <X className="h-4 w-4" />
              Abbrechen
            </Button>
          ) : (
            <Button onClick={onClose}>Schließen</Button>
          )}
          {isRunning && (
            <span className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              läuft …
            </span>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PhaseStep({
  label,
  active,
  done,
  error,
}: {
  label: string;
  active: boolean;
  done?: boolean;
  error?: boolean;
}) {
  let icon;
  if (error) {
    icon = <X className="h-4 w-4 text-red-600" />;
  } else if (done) {
    icon = <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  } else if (active) {
    icon = <Loader2 className="h-4 w-4 animate-spin text-blue-600" />;
  } else {
    icon = <div className="h-4 w-4 rounded-full border-2 border-slate-300" />;
  }
  return (
    <div className="flex items-center gap-2 text-sm">
      {icon}
      <span className={active ? "font-medium" : "text-slate-500"}>{label}</span>
    </div>
  );
}
