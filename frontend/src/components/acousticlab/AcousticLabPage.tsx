"use client";

import { useState } from "react";
import { Activity, Download, Info, Loader2, RefreshCw, Trash2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import {
  useAcousticTrials,
  useDeleteSamples,
  useSamplesStatus,
} from "@/hooks/queries/use-acousticlab";

import AcousticLabHelp from "./AcousticLabHelp";
import AcousticLabList from "./AcousticLabList";
import BulkProgress from "./BulkProgress";
import SampleLoadModal from "./SampleLoadModal";

export default function AcousticLabPage() {
  const { toast } = useToast();
  const trialsQuery = useAcousticTrials();
  const samplesStatus = useSamplesStatus();
  const deleteSamplesMut = useDeleteSamples();
  const [bulkOpen, setBulkOpen] = useState(false);
  const [sampleOpen, setSampleOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [forceRecompute, setForceRecompute] = useState(false);

  const trials = trialsQuery.data ?? [];
  const total = trials.length;
  const computed = trials.filter((t) => t.acoustic_computed).length;
  const pending = total - computed;
  const queueSize = forceRecompute ? total : pending;
  const nDemoImported = samplesStatus.data?.n_imported ?? 0;

  const handleDeleteDemos = async () => {
    try {
      const res = await deleteSamplesMut.mutateAsync();
      toast({
        title: "Demo-Daten entfernt",
        description: `${res.patients_deleted} Patienten · ${res.mp3_deleted} MP3-Dateien gelöscht`,
      });
    } catch (e) {
      toast({
        title: "Fehler",
        description: (e as Error).message,
        variant: "destructive",
      });
    } finally {
      setConfirmDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2">
            <Activity className="h-7 w-7 text-blue-600" />
            AcousticLab
          </h1>
          <p className="text-slate-500 text-sm mt-1 flex items-center gap-1.5">
            <span>
              Akustische Stimmanalyse pro Trial — Jitter, Shimmer, MFCC, HNR, F0.
              Score gegen alters- &amp; geschlechts-gematchte Kontrollkohorte.
            </span>
            <button
              type="button"
              onClick={() => setHelpOpen(true)}
              aria-label="Erklärung anzeigen"
              className="inline-flex items-center justify-center h-5 w-5 rounded-full text-blue-600 hover:bg-blue-50 transition-colors"
              title="Wie wird der Score berechnet?"
            >
              <Info className="h-4 w-4" />
            </button>
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Button
            variant="outline"
            onClick={() => setSampleOpen(true)}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Demo-Daten laden
            {nDemoImported > 0 && (
              <span className="text-xs text-slate-500">({nDemoImported} aktiv)</span>
            )}
          </Button>
          {nDemoImported > 0 && (
            <Button
              variant="ghost"
              onClick={() => setConfirmDelete(true)}
              disabled={deleteSamplesMut.isPending}
              className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              {deleteSamplesMut.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Demo entfernen
            </Button>
          )}
          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <Checkbox
              checked={forceRecompute}
              onCheckedChange={(v) => setForceRecompute(v === true)}
            />
            <span>Alle neu berechnen</span>
          </label>
          <Button
            disabled={queueSize === 0 || trialsQuery.isLoading}
            onClick={() => setBulkOpen(true)}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            {forceRecompute
              ? `Alle ${total} neu berechnen`
              : `${pending} ausstehende berechnen`}
          </Button>
        </div>
      </header>

      <div className="text-sm text-slate-600">
        {trialsQuery.isLoading ? (
          <span className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Lade Trials …
          </span>
        ) : trialsQuery.isError ? (
          <span className="text-red-600">
            Fehler: {(trialsQuery.error as Error).message}
          </span>
        ) : (
          <span>
            {computed} von {total} Trials haben Acoustic-Features berechnet.
          </span>
        )}
      </div>

      <AcousticLabList trials={trials} />

      {bulkOpen && (
        <BulkProgress
          trials={forceRecompute ? trials : trials.filter((t) => !t.acoustic_computed)}
          onClose={() => setBulkOpen(false)}
        />
      )}
      {sampleOpen && <SampleLoadModal onClose={() => setSampleOpen(false)} />}

      <AcousticLabHelp open={helpOpen} onClose={() => setHelpOpen(false)} />

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Demo-Daten wirklich entfernen?</AlertDialogTitle>
            <AlertDialogDescription>
              {nDemoImported} Demo-Patienten (Präfix <code className="text-xs bg-slate-100 px-1 rounded">DEMO-MDVR-</code>)
              werden mit allen Visits, Trials, Akustik-Features und MP3-Dateien gelöscht.
              Echte Patientendaten bleiben unberührt. Der ZIP-Cache wird nicht angefasst,
              ein erneutes Laden ist also schnell.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteDemos}
              className="bg-red-600 hover:bg-red-700"
            >
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
