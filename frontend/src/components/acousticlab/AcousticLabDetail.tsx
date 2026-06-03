"use client";

import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useTrialScore } from "@/hooks/queries/use-acousticlab";

interface Props {
  trialId: number | null;
  onClose: () => void;
}

const SHAP_TOP = [
  "mfcc_3_mean",
  "mfcc_11_mean",
  "mfcc_5_mean",
  "shimmer_local",
  "jitter_local",
  "jitter_rap",
  "hnr_mean_db",
];

function fmtPctl(p: number | null): string {
  if (p == null) return "—";
  return `${(p * 100).toFixed(0)}%`;
}

function fmt(value: number | null | undefined, digits = 4): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

export default function AcousticLabDetail({ trialId, onClose }: Props) {
  const { data, isLoading, isError, error } = useTrialScore(trialId);

  return (
    <Sheet open={trialId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Trial #{trialId} · Akustische Auswertung</SheetTitle>
          <SheetDescription>
            PD_Voice_Age_Score und Per-Feature-Percentile gegen die alters-
            &amp; geschlechts-gematchte Referenzkohorte.
          </SheetDescription>
        </SheetHeader>

        {isLoading && (
          <div className="flex items-center gap-2 mt-8 text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Lade …
          </div>
        )}
        {isError && (
          <div className="mt-8 text-red-600 text-sm">
            Fehler: {(error as Error).message}
          </div>
        )}

        {data && (
          <div className="mt-6 space-y-6">
            {/* Cell + Score panel */}
            <div className="rounded-lg border p-4 bg-slate-50">
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <Badge variant="outline">Patient {data.patient_cd ?? "?"}</Badge>
                <Badge variant="outline">{data.gender}</Badge>
                <Badge variant="outline">{data.age_band}</Badge>
                {data.group && <Badge>{data.group}</Badge>}
                <Badge
                  variant={
                    data.confidence === "high"
                      ? "default"
                      : data.confidence === "med"
                      ? "secondary"
                      : "outline"
                  }
                >
                  Confidence: {data.confidence}
                </Badge>
              </div>

              <div className="mt-4">
                <div className="text-sm text-slate-500">PD_Voice_Age_Score</div>
                <div className="text-4xl font-bold tabular-nums mt-1">
                  {data.score == null ? "n/a" : data.score.toFixed(3)}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {data.score == null
                    ? `Score nicht berechenbar (n_features_used=${data.n_features_used}). Vermutlich keine Parkinson-Referenzkohorte für diese Zelle.`
                    : `LLR=${data.log_likelihood_ratio?.toFixed(2)} · ${data.n_features_used} Features verwendet`}
                </div>
              </div>
            </div>

            {/* SHAP-top features highlighted */}
            <div>
              <h3 className="font-semibold mb-2 text-sm">SHAP-Top-Features (Shen et al. 2025)</h3>
              <FeatureTable
                features={SHAP_TOP.filter((f) => data.per_feature[f])}
                data={data.per_feature}
              />
            </div>

            {/* All features collapsible-ish */}
            <details className="group">
              <summary className="cursor-pointer text-sm font-semibold text-slate-700 hover:text-slate-900">
                Alle {Object.keys(data.per_feature).length} Features anzeigen
              </summary>
              <div className="mt-3">
                <FeatureTable
                  features={Object.keys(data.per_feature).sort()}
                  data={data.per_feature}
                />
              </div>
            </details>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function FeatureTable({
  features,
  data,
}: {
  features: string[];
  data: Record<string, { value: number; percentile_control: number | null; percentile_pd: number | null; n_control: number; n_pd: number }>;
}) {
  return (
    <div className="border rounded-md overflow-hidden text-xs">
      <div className="grid grid-cols-[1fr_90px_80px_80px_60px_60px] bg-slate-100 px-3 py-2 font-semibold text-slate-600">
        <span>Feature</span>
        <span className="text-right">Value</span>
        <span className="text-right">% Control</span>
        <span className="text-right">% PD</span>
        <span className="text-right">n_C</span>
        <span className="text-right">n_PD</span>
      </div>
      {features.map((f) => {
        const e = data[f];
        if (!e) return null;
        return (
          <div
            key={f}
            className="grid grid-cols-[1fr_90px_80px_80px_60px_60px] px-3 py-1.5 border-t hover:bg-slate-50"
          >
            <span className="font-mono text-[11px]">{f}</span>
            <span className="text-right tabular-nums">{fmt(e.value)}</span>
            <span className="text-right tabular-nums">{fmtPctl(e.percentile_control)}</span>
            <span className="text-right tabular-nums">{fmtPctl(e.percentile_pd)}</span>
            <span className="text-right text-slate-500">{e.n_control}</span>
            <span className="text-right text-slate-500">{e.n_pd}</span>
          </div>
        );
      })}
    </div>
  );
}
