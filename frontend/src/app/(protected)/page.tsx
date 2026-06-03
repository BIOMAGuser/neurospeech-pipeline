"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Loader2, Database, Bot, Users, FileText, FlaskConical, ArrowRight, Info, CircleHelp } from "lucide-react";
import { useHealth, useStats, useOpenAIStatus } from "@/hooks/queries/use-dashboard";

function StatusDot({ ok }: { ok: boolean | null }) {
  if (ok === null) return <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />;
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  );
}

export default function DashboardPage() {
  const { data: health, isPending: healthPending } = useHealth();
  const { data: stats, isPending: statsPending } = useStats();
  const { data: openai, isPending: openaiPending } = useOpenAIStatus();

  const loading = healthPending || statsPending || openaiPending;
  const dbOk = health ? health.status === "ok" : null;
  const openaiOk = openai ? openai.status === "ok" : null;

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Status row: DB + OpenAI side by side */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="py-3">
            <CardContent className="flex items-center gap-3 p-4 pb-0">
              <Database className="h-5 w-5 text-blue-600 shrink-0" />
              <div className="flex items-center gap-2">
                <StatusDot ok={dbOk} />
                <span className="text-sm font-medium">
                  {dbOk === null ? "Datenbank..." : dbOk ? "DB verbunden" : "DB offline"}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card className="py-3">
            <CardContent className="flex items-center gap-3 p-4 pb-0">
              <Bot className="h-5 w-5 text-purple-600 shrink-0" />
              <div className="flex items-center gap-2">
                <StatusDot ok={openaiOk} />
                <span className="text-sm font-medium">
                  {openaiOk === null ? "OpenAI..." : openaiOk ? "OpenAI OK" : "OpenAI offline"}
                </span>
                {openaiOk === false && openai?.reason && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="p-1"><Info className="h-5 w-5 text-red-400 cursor-help" /></span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-xs">
                      <p className="text-sm">{openai.reason}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Primary CTA: Neue Messung */}
        {openaiOk === false ? (
          <Card className="bg-gradient-to-r from-slate-400 to-slate-500 text-white shadow-md">
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <div className="text-lg font-semibold">Neue Messung starten</div>
                <div className="text-slate-200 text-sm mt-0.5">
                  Kein gültiger API-Key — bitte unter Einstellungen hinterlegen
                </div>
              </div>
              <Link href="/settings">
                <Button variant="secondary" className="shrink-0">
                  Einstellungen
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <Link href="/measurement" className="block">
            <Card className="bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-700 hover:to-blue-800 transition-all cursor-pointer shadow-md hover:shadow-lg">
              <CardContent className="flex items-center justify-between p-5">
                <div>
                  <div className="text-lg font-semibold">Neue Messung starten</div>
                  <div className="text-blue-100 text-sm mt-0.5">Wizard: Patientendaten, Aufnahmen, Auswertung</div>
                </div>
                <ArrowRight className="h-6 w-6 text-blue-200" />
              </CardContent>
            </Card>
          </Link>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-3 gap-3">
          <Card>
            <CardContent className="p-4 text-center">
              <Users className="h-5 w-5 text-teal-600 mx-auto mb-1" />
              <div className="text-2xl font-bold text-slate-800">
                {loading ? <Loader2 className="h-5 w-5 animate-spin mx-auto" /> : (stats?.patients ?? "–")}
              </div>
              <div className="text-xs text-slate-500">Patienten</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <FileText className="h-5 w-5 text-orange-600 mx-auto mb-1" />
              <div className="text-2xl font-bold text-slate-800">
                {loading ? <Loader2 className="h-5 w-5 animate-spin mx-auto" /> : (stats?.analyses ?? "–")}
              </div>
              <div className="text-xs text-slate-500">Analysen</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <FlaskConical className="h-5 w-5 text-indigo-600 mx-auto mb-1" />
              <div className="text-2xl font-bold text-slate-800">
                {loading ? <Loader2 className="h-5 w-5 animate-spin mx-auto" /> : (stats?.trials ?? "–")}
              </div>
              <div className="text-xs text-slate-500">Trials</div>
            </CardContent>
          </Card>
        </div>

        {/* Secondary: Verlauf */}
        <Link href="/history">
          <Button variant="outline" className="w-full">
            Verlauf anzeigen
          </Button>
        </Link>

        {/* Copyright Footer */}
        <div className="flex items-center justify-center gap-2 pt-6 text-xs text-slate-400">
          <span>&copy; {new Date().getFullYear()} Stefan Brodoehl, Lydia Justi</span>
          <Link href="/about" className="text-slate-400 hover:text-blue-500 transition-colors">
            <CircleHelp className="h-5 w-5" />
          </Link>
        </div>
      </div>
    </TooltipProvider>
  );
}
