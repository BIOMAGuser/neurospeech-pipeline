"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function AcousticLabHelp({ open, onClose }: Props) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>AcousticLab — Was wird hier berechnet?</DialogTitle>
          <DialogDescription>
            Akustische Stimmanalyse pro Trial mit Bayesian-Score gegen eine
            alters- und geschlechts-gematchte Kontrollkohorte.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 text-sm leading-relaxed">
          {/* Was die Liste zeigt */}
          <section>
            <h3 className="font-semibold text-base mb-1">Die Liste</h3>
            <p>
              Jede Zeile ist ein Trial mit Audio-Aufnahme. Spalten: Patient·Task,
              Geschlecht (♂/♀/⚧), Altersband, Studiengruppe (Kontrolle/Parkinson/
              Sonstiges), Audio-Dauer, Berechnungsstatus, Score-Badge und Aktionen.
              Klick auf eine Zeile öffnet die Detail-Ansicht mit allen 39 Features
              und ihren Percentilen gegenüber der Referenzkohorte.
            </p>
          </section>

          {/* Features */}
          <section>
            <h3 className="font-semibold text-base mb-1">39 akustische Features</h3>
            <p className="mb-2">
              Berechnet mit{" "}
              <code className="text-xs bg-slate-100 px-1 rounded">parselmouth</code>
              {" "}(Praat-Wrapper) direkt aus dem MP3 (auf 16 kHz mono normalisiert):
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>F0 (Grundfrequenz)</strong> — mean / std / min / max in Hz.
                Aus voiced frames der Praat-Pitch-Detection (75–500 Hz).
              </li>
              <li>
                <strong>Jitter</strong> — local, RAP, PPQ5. Periodendauer-Variation
                der Stimmlippen-Schwingung. Erhöht bei Dysphonie/PD.
              </li>
              <li>
                <strong>Shimmer</strong> — local, APQ3, APQ5, APQ11. Amplituden-Variation.
              </li>
              <li>
                <strong>HNR</strong> (Harmonics-to-Noise Ratio) — mean / std in dB.
                Sinkt bei rauerer/atemiger Stimme.
              </li>
              <li>
                <strong>MFCC-13</strong> — mean + std je Koeffizient (26 Werte).
                Spektrale Charakteristik des Vokaltrakts.
              </li>
            </ul>
            <p className="mt-2 text-slate-600">
              Per-Feature-Failures (z. B. zu still, zu kurz) liefern{" "}
              <code className="text-xs bg-slate-100 px-1 rounded">null</code> statt
              den ganzen Trial fehlschlagen zu lassen.
            </p>
          </section>

          {/* Kohorte */}
          <section>
            <h3 className="font-semibold text-base mb-1">Referenzkohorte</h3>
            <p className="mb-2">
              Die Kohorte wird <strong>aus der eigenen DB live aggregiert</strong> —
              keine externen Tabellen, keine vortrainierten Modelle. Achsen:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Geschlecht</strong> — m / f / d / unknown
              </li>
              <li>
                <strong>Altersband</strong> — 10-Jahres-Buckets (20-29 … 90+) oder unknown
              </li>
              <li>
                <strong>Gruppe</strong> — Kontrolle oder Parkinson. Trials mit
                Gruppe „Sonstiges" oder leer sind aus der Referenz ausgeschlossen,
                können aber selbst trotzdem gescort werden.
              </li>
            </ul>
            <p className="mt-2">
              Pro (Geschlecht × Altersband × Gruppe × Feature) wird ein
              <strong> Normal-Inverse-Gamma Posterior</strong> in geschlossener Form
              gefittet — kein MCMC, kein numerisches Optimieren. Mit jeder neuen
              Messung wird die Posterior aktualisiert (Konjugat-Update).
              Die <strong>posterior predictive</strong> ist eine Student-t-Verteilung
              mit ν=2α<sub>n</sub> Freiheitsgraden.
            </p>
          </section>

          {/* Score */}
          <section>
            <h3 className="font-semibold text-base mb-1">PD_Voice_Age_Score</h3>
            <p className="mb-2">
              Score ∈ [0,1]. Höher = ähnelt eher der Parkinson-Kohorte; niedriger =
              ähnelt eher der Kontrollkohorte. Berechnung pro Trial:
            </p>
            <ol className="list-decimal pl-5 space-y-1">
              <li>
                Patient-Zelle bestimmen (sein Geschlecht × Altersband).
              </li>
              <li>
                Posterior für Kontroll- und PD-Gruppe in dieser Zelle abrufen
                (mit Fallback auf gröbere Zellen wenn n &lt; 10).
              </li>
              <li>
                Für jede der 7 SHAP-Top-Features den Log-Likelihood-Quotient
                berechnen:{" "}
                <code className="text-xs bg-slate-100 px-1 rounded">
                  log p(x | PD) − log p(x | Kontrolle)
                </code>
              </li>
              <li>
                Summieren mit Gewichten (vorerst alle 1) →{" "}
                <code className="text-xs bg-slate-100 px-1 rounded">LLR</code>
              </li>
              <li>
                Score = sigmoid(LLR)
              </li>
            </ol>
            <p className="mt-2">
              <strong>SHAP-Top-Features</strong> (aus Shen et al. 2025): mfcc_3_mean,
              mfcc_11_mean, mfcc_5_mean, shimmer_local, jitter_local, jitter_rap,
              hnr_mean_db. Diese werden im Score gewichtet — Werte für alle 39 Features
              sind aber im Detail-Sheet einsehbar.
            </p>
            <p className="mt-2">
              Wenn eine Seite (Kontrolle oder PD) für die Zelle keine Daten hat,
              gibt's keinen Score (
              <code className="text-xs bg-slate-100 px-1 rounded">null</code>) und
              die Zeile zeigt <em>n/a</em>.
            </p>
          </section>

          {/* Per-Feature-Percentile */}
          <section>
            <h3 className="font-semibold text-base mb-1">Per-Feature-Percentile</h3>
            <p>
              Im Detail-Sheet sieht man pro Feature den Wert sowie:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>% Control</strong> — Position des Werts in der CDF der
                Kontroll-Posterior. 50 % = Median der gesunden Kohorte; ≥ 95 % oder
                ≤ 5 % = Ausreißer.
              </li>
              <li>
                <strong>% PD</strong> — analog für die Parkinson-Kohorte.
              </li>
              <li>
                <strong>n_C / n_PD</strong> — wie viele Beobachtungen in der jeweiligen
                Zelle die Posterior tragen.
              </li>
            </ul>
          </section>

          {/* Confidence */}
          <section>
            <h3 className="font-semibold text-base mb-1">Confidence-Stufen</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>high</strong> — ≥ 10 Samples in beiden Posteriors der
                Patient-Zelle. Score ist robust.
              </li>
              <li>
                <strong>med</strong> — ≥ 5 Samples.
              </li>
              <li>
                <strong>low</strong> — &lt; 5 oder Fallback auf gröbere Zelle nötig.
                Posterior ist breit, Score-Signal noch schwach.
              </li>
            </ul>
            <p className="mt-2 text-slate-600">
              In der Liste-Spalte „Score" zeigen Zellen mit niedrigem Confidence
              ein graues „low conf"-Badge statt einer Zahl.
            </p>
          </section>

          {/* Score-Badge */}
          <section>
            <h3 className="font-semibold text-base mb-1">Score-Badge-Farben</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-600 text-white text-[10px] font-semibold">0.18</span>{" "}
                ≤ 0.30 — Kontroll-typisch
              </li>
              <li>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 text-[10px] font-semibold">0.50</span>{" "}
                0.30 – 0.70 — gemischt / unsicher
              </li>
              <li>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-red-600 text-white text-[10px] font-semibold">0.81</span>{" "}
                ≥ 0.70 — PD-typisch
              </li>
            </ul>
          </section>

          {/* Methodik / Quellen */}
          <section>
            <h3 className="font-semibold text-base mb-1">Methodik &amp; Quellen</h3>
            <ul className="list-disc pl-5 space-y-1 text-slate-700">
              <li>
                Shen, Mortezaagha, Rahgozar (2025).{" "}
                <em>Explainable AI to diagnose early Parkinson's disease via voice
                analysis</em>. Sci Rep 15:11687.
              </li>
              <li>
                MDVR-KCL Demo-Datensatz (Jaeger et al., King's College London) —
                Zenodo DOI{" "}
                <code className="text-xs bg-slate-100 px-1 rounded">
                  10.5281/zenodo.2867216
                </code>
                , CC-BY-4.0.
              </li>
              <li>
                Praat / parselmouth — Standard-Settings (Pitch-Range 75–500 Hz,
                Period-Range 0.0001–0.02 s, max-period-factor 1.3).
              </li>
              <li>
                Conjugate-Prior NIG: μ ~ N(μ₀, σ²/κ₀), σ² ~ InvGamma(α₀, β₀) mit
                schwach informativem Prior (μ₀=0, κ₀=1, α₀=1, β₀=1).
              </li>
            </ul>
          </section>

          {/* Demo-Daten */}
          <section>
            <h3 className="font-semibold text-base mb-1">Demo-Daten</h3>
            <p>
              Über den <strong>„Demo-Daten laden"</strong>-Button werden 37 Sprecher
              (16 PD + 21 HC) aus dem MDVR-KCL-Datensatz geladen. Patient-IDs
              haben das Präfix{" "}
              <code className="text-xs bg-slate-100 px-1 rounded">DEMO-MDVR-</code>.
              Geschlecht und Geburtsdatum sind <em>deterministisch synthetisiert</em>
              {" "}aus dem File-Hash (PD: 55–85 Jahre, HC: 30–75 Jahre, m/f 50/50) —
              MDVR-KCL liefert nur klinische Scores, keine Demografie. Diese
              Patienten sind global sichtbar (alle Nutzer) und können über
              <strong> „Demo entfernen"</strong> wieder weggeräumt werden.
            </p>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
