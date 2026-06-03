"use client";

import { useSearchParams } from "next/navigation";
import HistoryList from "@/components/history/HistoryList";
import AnalysisDetailView from "@/components/history/AnalysisDetail";

export default function HistoryPage() {
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id");

  if (idParam) {
    return <AnalysisDetailView id={Number(idParam)} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Verlauf</h1>
        <p className="text-slate-600 mt-1">
          Übersicht aller Patienten und deren Analysen.
        </p>
      </div>
      <HistoryList />
    </div>
  );
}
