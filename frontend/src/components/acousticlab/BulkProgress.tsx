"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

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
import { computeAcoustic } from "@/services/acousticlab";
import type { AcousticTrialRow } from "@/types/acousticlab";

interface Props {
  trials: AcousticTrialRow[];
  onClose: () => void;
}

export default function BulkProgress({ trials, onClose }: Props) {
  const { toast } = useToast();
  const qc = useQueryClient();
  const [done, setDone] = useState(0);
  const [errors, setErrors] = useState<{ trial_id: number; msg: string }[]>([]);
  const [running, setRunning] = useState(true);
  const [currentTrialId, setCurrentTrialId] = useState<number | null>(null);
  const abortRef = useRef(new AbortController());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const errs: { trial_id: number; msg: string }[] = [];
      for (let i = 0; i < trials.length; i++) {
        if (cancelled || abortRef.current.signal.aborted) break;
        const t = trials[i];
        setCurrentTrialId(t.trial_id);
        try {
          await computeAcoustic(t.trial_id, abortRef.current.signal);
        } catch (e) {
          errs.push({ trial_id: t.trial_id, msg: (e as Error).message });
        }
        if (!cancelled) setDone(i + 1);
      }
      if (!cancelled) {
        setRunning(false);
        setErrors(errs);
        qc.invalidateQueries({ queryKey: ["acoustic-trials"] });
        qc.invalidateQueries({ queryKey: ["acoustic-cohort"] });
        toast({
          title: errs.length > 0 ? "Fertig mit Fehlern" : "Alle Trials berechnet",
          description: `${trials.length - errs.length} erfolgreich · ${errs.length} Fehler`,
          variant: errs.length > 0 ? "destructive" : undefined,
        });
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const total = trials.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 100;
  const handleCancel = () => {
    abortRef.current.abort();
    setRunning(false);
  };

  return (
    <Dialog open onOpenChange={(o) => !o && !running && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {running ? "Bulk-Berechnung läuft …" : "Fertig"}
          </DialogTitle>
          <DialogDescription>
            {running
              ? `Trial ${currentTrialId ?? "?"} wird verarbeitet.`
              : `${done} von ${total} Trials verarbeitet.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <Progress value={pct} />
          <div className="text-sm text-slate-600 tabular-nums">
            {done}/{total} ({pct}%)
            {errors.length > 0 && (
              <span className="text-red-600 ml-2">· {errors.length} Fehler</span>
            )}
          </div>
          {!running && errors.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-red-700">
                Fehler-Details
              </summary>
              <ul className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                {errors.map((e) => (
                  <li key={e.trial_id} className="font-mono">
                    #{e.trial_id}: {e.msg}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>

        <DialogFooter>
          {running ? (
            <Button variant="outline" onClick={handleCancel} className="gap-1.5">
              <X className="h-4 w-4" />
              Abbrechen
            </Button>
          ) : (
            <Button onClick={onClose}>Schließen</Button>
          )}
          {running && (
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
