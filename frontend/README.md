# SpeechScribe Frontend

Next.js-basiertes Frontend für die SpeechScribe-Anwendung.

## 📁 Ordnerstruktur

```
frontend/
├── config/                    # Konfigurationsdateien & Beispiele
│   ├── .env.example          # Vorlage für .env.local
│   └── .env.production.example # Vorlage für .env.production
├── docs/                      # Dokumentation
├── public/                    # Statische Assets (Bilder, Icons, etc.)
├── scripts/                   # Shell-Skripte
│   ├── start-frontend.sh     # Dev Server starten
│   └── build-frontend.sh     # Production Build
├── src/
│   ├── app/                   # Next.js App Router (Seiten & Layouts)
│   │   ├── login/            # Login-Seite
│   │   ├── layout.tsx        # Root Layout
│   │   ├── page.tsx          # Hauptseite (Dashboard)
│   │   ├── globals.css       # Globale CSS-Styles
│   │   └── favicon.ico
│   ├── components/           # React-Komponenten
│   │   ├── ui/               # UI-Komponenten (Button, Card, Input, etc.)
│   │   ├── AudioRecorder.tsx    # Audio-Aufnahme
│   │   ├── AudioProcessor.tsx   # Audio-Verarbeitung
│   │   ├── MetricsDisplay.tsx   # Metriken-Anzeige
│   │   ├── ResultsVisualization.tsx  # Ergebnisvisualisierung
│   │   └── ...               # Weitere Komponenten
│   ├── hooks/                # Custom React Hooks
│   ├── lib/                  # Utility-Funktionen & Helper
│   ├── services/             # API-Services (Backend-Kommunikation)
│   └── types/                # TypeScript Type-Definitionen
├── .env.local                # Lokale Umgebungsvariablen (NICHT in Git)
├── .env.production           # Produktions-Umgebungsvariablen
├── package.json              # NPM Dependencies
├── next.config.ts            # Next.js Konfiguration
├── tsconfig.json             # TypeScript Konfiguration
├── tailwind.config.ts        # Tailwind CSS Konfiguration
├── postcss.config.mjs        # PostCSS Konfiguration
└── README.md                 # Diese Datei
```

## 🚀 Quick Start

```bash
# Installation
npm install

# Lokale Entwicklung (Port 3000)
npm run dev
# oder
./scripts/start-frontend.sh

# Production Build
npm run build
npm start

# Linting
npm run lint
```

## 🔧 Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `next.config.ts` | Next.js Konfiguration |
| `tsconfig.json` | TypeScript Einstellungen |
| `tailwind.config.ts` | Tailwind CSS Theme & Plugins |
| `postcss.config.mjs` | CSS Post-Processing |
| `components.json` | Shadcn/UI Konfiguration |

## 📚 Umgebungsvariablen

```bash
NEXT_PUBLIC_API_URL=http://localhost/api  # Backend API URL (via Nginx)
```

## 🐳 Docker

Das Frontend läuft im Docker-Container:
- **Image**: `speechscribe-frontend`
- **Port**: 3000 (intern, via Nginx auf Port 80 erreichbar)
- **Dockerfile**: `../docker/Dockerfile.frontend`

## 📖 Weitere Dokumentation

Siehe `docs/` Ordner für detaillierte Dokumentation.

