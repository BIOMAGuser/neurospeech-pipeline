"use client";

import { Fragment, useRef, useState } from "react";
import Link from "next/link";
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
import { Loader2, Trash2, Download, Upload, Users, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { usePatients, usePatientAnalyses } from "@/hooks/queries/use-history";
import { deleteAnalysis, deletePatient, exportPatient, exportAnalysis, importPatientJson, importAnalysisJson } from "@/services/history";
import { useQueryClient } from "@tanstack/react-query";

type DeleteTarget =
  | { type: "patient"; id: number; label: string }
  | { type: "analysis"; id: number; label: string };

export default function HistoryList() {
  const { data: patients, isPending: loading, error: queryError } = usePatients();
  const error = queryError?.message ?? null;
  const [expandedPatient, setExpandedPatient] = useState<number | null>(null);
  const { data: analyses, isPending: loadingAnalyses } = usePatientAnalyses(expandedPatient);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const downloadJson = (data: unknown, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPatient = async (id: number, patientId: string) => {
    try {
      const data = await exportPatient(id);
      downloadJson(data, `${patientId}_fhir.json`);
    } catch {
      toast({ title: "Export fehlgeschlagen", variant: "destructive" });
    }
  };

  const handleExportAnalysis = async (id: number, date: string, patientId: string) => {
    try {
      const data = await exportAnalysis(id);
      downloadJson(data, `${patientId}_${date}_fhir.json`);
    } catch {
      toast({ title: "Export fehlgeschlagen", variant: "destructive" });
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      if (deleteTarget.type === "patient") {
        await deletePatient(deleteTarget.id);
        if (expandedPatient === deleteTarget.id) setExpandedPatient(null);
        toast({ title: "Patient gelöscht", description: "Patient und alle Analysen wurden entfernt." });
      } else {
        await deleteAnalysis(deleteTarget.id);
        toast({ title: "Analyse gelöscht", description: "Die Analyse wurde erfolgreich entfernt." });
      }
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      queryClient.invalidateQueries({ queryKey: ["patient-analyses"] });
    } catch {
      toast({ title: "Fehler beim Löschen", variant: "destructive" });
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // Reset so the same file can be re-selected
    e.target.value = "";

    if (file.size > 10 * 1024 * 1024) {
      toast({ title: "Datei zu groß", description: "Maximale Dateigröße: 10 MB.", variant: "destructive" });
      return;
    }

    setImporting(true);
    try {
      const text = await file.text();
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(text);
      } catch {
        toast({ title: "Import fehlgeschlagen", description: "Ungültige JSON-Datei.", variant: "destructive" });
        return;
      }

      // FHIR Bundle or legacy format — always use patient import (backend handles both)
      const summary = data.resourceType === "Bundle"
        ? await importPatientJson(data)
        : data.patient
          ? await importPatientJson(data)
          : data.analysis
            ? await importAnalysisJson(data)
            : null;

      if (!summary) {
        toast({ title: "Unbekanntes JSON-Format", variant: "destructive" });
        return;
      }

      const parts: string[] = [];
      if (summary.patients_created) parts.push(`${summary.patients_created} Patient(en) erstellt`);
      if (summary.analyses_created) parts.push(`${summary.analyses_created} Analyse(n) erstellt`);
      if (summary.analyses_skipped) parts.push(`${summary.analyses_skipped} Analyse(n) übersprungen`);
      if (summary.trials_created) parts.push(`${summary.trials_created} Trial(s) erstellt`);

      toast({
        title: "Import erfolgreich",
        description: parts.join(", ") || "Keine neuen Daten importiert.",
      });
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      queryClient.invalidateQueries({ queryKey: ["patient-analyses"] });
    } catch (err) {
      toast({
        title: "Import fehlgeschlagen",
        description: err instanceof Error ? err.message : "Unbekannter Fehler",
        variant: "destructive",
      });
    } finally {
      setImporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600 text-sm">Fehler beim Laden: {error}</div>
    );
  }

  if (!patients || patients.length === 0) {
    return (
      <>
        <input
          type="file"
          accept=".json"
          ref={fileInputRef}
          className="hidden"
          onChange={handleImportFile}
        />
        <div className="text-center py-16">
          <Users className="h-10 w-10 text-slate-200 mx-auto mb-3" />
          <p className="text-slate-400 text-sm mb-4">Noch keine Patienten vorhanden.</p>
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
          >
            {importing ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
            Importieren
          </Button>
        </div>
      </>
    );
  }

  return (
    <>
      <input
        type="file"
        accept=".json"
        ref={fileInputRef}
        className="hidden"
        onChange={handleImportFile}
      />
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-400">
          {patients.length} {patients.length === 1 ? "Patient" : "Patienten"}
        </span>
        <Button
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={importing}
        >
          {importing ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
          Importieren
        </Button>
      </div>
      <div className="border border-slate-200 rounded-lg bg-white overflow-hidden">
        {/* Column header */}
        <div className="grid grid-cols-[20px_1fr_80px_100px_60px_80px] md:grid-cols-[20px_1fr_80px_100px_100px_60px_80px] gap-x-2 px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-500 uppercase tracking-wide">
          <span />
          <span>Patient-ID</span>
          <span>Geschlecht</span>
          <span className="hidden md:block">Geburtsdatum</span>
          <span>Erstellt</span>
          <span className="text-right">Anz.</span>
          <span />
        </div>

        {/* Patient rows */}
        <div className="divide-y divide-slate-100">
          {patients.map((p) => {
            const isExpanded = expandedPatient === p.id;

            return (
              <Fragment key={p.id}>
                <div
                  className="group grid grid-cols-[20px_1fr_80px_100px_60px_80px] md:grid-cols-[20px_1fr_80px_100px_100px_60px_80px] gap-x-2 items-center px-3 py-3.5 cursor-pointer hover:bg-blue-50/50 transition-colors text-sm"
                  onClick={() => setExpandedPatient(isExpanded ? null : p.id)}
                >
                  <ChevronRight
                    className={`h-3.5 w-3.5 text-slate-400 transition-transform duration-150 ${isExpanded ? "rotate-90" : ""}`}
                  />
                  <span className="font-medium text-slate-800 truncate flex items-center gap-1.5">
                    <span
                      className={`inline-block h-2 w-2 rounded-full shrink-0 ${
                        p.export_status === "full" ? "bg-emerald-400" : p.export_status === "partial" ? "bg-amber-400" : "bg-red-400"
                      }`}
                      title={
                        p.export_status === "full" ? "Vollständig exportiert" : p.export_status === "partial" ? "Teilweise exportiert" : "Nicht exportiert"
                      }
                    />
                    {p.patient_id}
                  </span>
                  <span className="text-slate-500 truncate">{p.gender || "–"}</span>
                  <span className="text-slate-500 truncate hidden md:block">{p.birth_date || "–"}</span>
                  <span className="text-slate-400 truncate">
                    {p.created_at ? new Date(p.created_at).toLocaleDateString("de-DE") : "–"}
                  </span>
                  <span className="text-slate-500 text-right tabular-nums">{p.analysis_count}</span>
                  <span className="flex gap-2">
                    <button
                      className="p-2.5 rounded text-slate-400 hover:text-blue-500 hover:bg-blue-50"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleExportPatient(p.id, p.patient_id);
                      }}
                      title="Patient exportieren"
                    >
                      <Download className="h-5 w-5" />
                    </button>
                    <button
                      className="p-2.5 rounded text-slate-400 hover:text-red-500 hover:bg-red-50"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget({ type: "patient", id: p.id, label: p.patient_id });
                      }}
                      title="Patient löschen"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </span>
                </div>

                {/* Analyses sub-rows */}
                {isExpanded && (
                  <div className="bg-slate-50/70">
                    {loadingAnalyses ? (
                      <div className="flex justify-center py-3">
                        <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                      </div>
                    ) : !analyses || analyses.length === 0 ? (
                      <p className="text-xs text-slate-400 py-3 pl-9">Keine Analysen.</p>
                    ) : (
                      <div className="divide-y divide-slate-100/80">
                        {/* Analysis column header */}
                        <div className="grid grid-cols-[28px_100px_80px_60px_60px_1fr_80px] gap-x-2 px-3 py-2.5 text-[11px] font-medium text-slate-400 uppercase tracking-wide">
                          <span />
                          <span>Datum</span>
                          <span>Gruppe</span>
                          <span>MoCA</span>
                          <span className="text-right">Trials</span>
                          <span />
                          <span />
                        </div>
                        {analyses.map((a) => (
                          <Link
                            key={a.id}
                            href={`/history?id=${a.id}`}
                            className="group/a grid grid-cols-[28px_100px_80px_60px_60px_1fr_80px] gap-x-2 items-center px-3 py-3 text-sm hover:bg-blue-50/60 transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span className="flex justify-center">
                              <span
                                className={`inline-block h-1.5 w-1.5 rounded-full ${a.exported_at ? "bg-emerald-400" : "bg-red-400"}`}
                                title={a.exported_at ? `Exportiert am ${new Date(a.exported_at).toLocaleDateString("de-DE")}` : "Nicht exportiert"}
                              />
                            </span>
                            <span className="text-slate-700">{a.date || "–"}</span>
                            <span className="text-slate-500">{a.group || "–"}</span>
                            <span className="text-slate-500">{a.moca_score ?? "–"}</span>
                            <span className="text-slate-500 text-right tabular-nums">{a.trial_count}</span>
                            <span />
                            <span className="flex gap-2">
                              <button
                                className="p-2.5 rounded text-slate-400 hover:text-blue-500 hover:bg-blue-50"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleExportAnalysis(a.id, a.date || "unknown", p.patient_id);
                                }}
                                title="Analyse exportieren"
                              >
                                <Download className="h-5 w-5" />
                              </button>
                              <button
                                className="p-2.5 rounded text-slate-400 hover:text-red-500 hover:bg-red-50"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  setDeleteTarget({ type: "analysis", id: a.id, label: a.date || "" });
                                }}
                                title="Analyse löschen"
                              >
                                <Trash2 className="h-5 w-5" />
                              </button>
                            </span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Fragment>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-200" />
      </div>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {deleteTarget?.type === "patient" ? "Patient löschen?" : "Analyse löschen?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget?.type === "patient"
                ? `Möchten Sie "${deleteTarget.label}" und alle zugehörigen Analysen unwiderruflich löschen?`
                : `Möchten Sie die Analyse${deleteTarget?.label ? ` vom ${deleteTarget.label}` : ""} unwiderruflich löschen?`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {deleting ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : null}
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
