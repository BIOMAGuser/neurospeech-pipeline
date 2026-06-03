# Frontend Root Dateien Übersicht

Diese Dateien **müssen** im Root bleiben (werden von Tools erwartet):

| Datei | Zweck |
|-------|-------|
| `package.json` | NPM Dependencies & Scripts |
| `package-lock.json` | Dependency Lock File |
| `next.config.ts` | Next.js Konfiguration |
| `tsconfig.json` | TypeScript Konfiguration |
| `tailwind.config.ts` | Tailwind CSS Theme |
| `postcss.config.mjs` | PostCSS Konfiguration |
| `components.json` | Shadcn/UI Konfiguration |
| `next-env.d.ts` | Next.js TypeScript Typen (Auto-generiert) |
| `README.md` | Projekt-Dokumentation |
| `.gitignore` | Git Ignore Rules |

Diese Dateien **können** sein (optional):
| Datei | Zweck |
|-------|-------|
| `.env.local` | Lokale Umgebungsvariablen |
| `.env.production` | Production Umgebungsvariablen |
| `tsconfig.tsbuildinfo` | TypeScript Build Cache (Auto-generiert) |

Organisierte Dateien (in anderen Ordnern):
| Original → Neu | Ordner |
|---|---|
| `.eslintrc.json` | `config/` |
| `.dockerignore` | `docker/` (als `.dockerignore.frontend`) |

## Erklärung

- **Next.js erwartet** die meisten Config-Dateien im Root
- **Umgebungsvariablen** sollten im Root sein, damit Next.js sie automatisch lädt
- **ESLint & Docker Config** können sicher in andere Ordner verschoben werden
