# Frontend Komponenten

## Übersicht

Die Komponenten sind in zwei Kategorien unterteilt:

### UI-Komponenten (`components/ui/`)
Wiederverwendbare UI-Bausteine (Button, Card, Input, Dialog, etc.) basierend auf Shadcn/UI.

### Feature-Komponenten (`components/`)
Geschäftslogik-Komponenten spezifisch für SpeechScribe:

| Komponente | Zweck |
|-----------|-------|
| `AnalysisSection.tsx` | Analyse-Bereich mit Ergebnisanzeige |
| `AppHeader.tsx` | App-Header mit Navigation |
| `AudioRecorder.tsx` | Aufnahme von Audio vom Mikrofon |
| `AudioProcessor.tsx` | Verarbeitung von Audio (Konvertierung, Bereinigung) |
| `CookieTheftPicture.tsx` | Cookie-Theft-Bild fuer Bildbeschreibungsaufgabe |
| `MetricsDisplay.tsx` | Anzeige von berechneten Metriken |
| `PatientInfoForm.tsx` | Dynamisches Patientenformular (aus Backend-Config) |
| `PatientSearchDialog.tsx` | Patienten-Suche und -Auswahl |
| `ResultsVisualization.tsx` | Visualisierung der Analyseergebnisse |
| `SpacyAnalysis.tsx` | NLP-Analyse-Anzeige |
| `TaskRecordingSection.tsx` | Aufnahme-Bereich pro Task |
| `VersionBadge.tsx` | Versions-Information |

### Unterverzeichnisse

| Verzeichnis | Komponenten | Zweck |
|-------------|-------------|-------|
| `history/` | `HistoryList.tsx` | Patienten- & Analyse-Historie |
| `measurement/` | `MeasurementWizard.tsx`, `WizardStepper.tsx` | 3-Step Mess-Wizard |
| `providers/` | `AuthProvider.tsx`, `QueryProvider.tsx` | Context-Provider (Auth, React Query) |

## Komponenten-Beispiel

```typescript
import { AudioRecorder } from "@/components/AudioRecorder";

export default function Home() {
  return <AudioRecorder />;
}
```

## Shadcn/UI

Neue UI-Komponenten können mit folgendem Befehl hinzugefügt werden:

```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
```

Siehe [shadcn/ui Dokumentation](https://ui.shadcn.com)
