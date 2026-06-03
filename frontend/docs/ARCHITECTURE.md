# Frontend Architektur

## Stack

- **Framework**: Next.js 15.2.3 (React 19)
- **Sprache**: TypeScript
- **Styling**: Tailwind CSS
- **UI-Komponenten**: Shadcn/UI
- **State Management**: React Hooks (Context API falls benötigt)
- **HTTP-Client**: Fetch API
- **API-Kommunikation**: RESTful (via Nginx Reverse Proxy auf Port 80)

## Ordner-Struktur Erklärung

### `src/app/`
**Next.js App Router** - Definiert die Routes und Seitenlayouts:
- Dateisystem-basiertes Routing
- `page.tsx` = Route-Komponente
- `layout.tsx` = Gemeinsames Layout
- `globals.css` = Globale Styles

### `src/components/`
**React-Komponenten**:
- Wiederverwendbare UI-Teile
- Business-Logic für Audio/Metriken
- Organisiert nach Funktionalität

### `src/hooks/`
**Custom React Hooks**:
- `use-audio-processor` - Audio-Verarbeitung
- `use-patient` - Patienten-Logik
- `use-results-processing` - Ergebnis-Aufbereitung
- `use-toast` - Toast-Benachrichtigungen
- `queries/` - React-Query Hooks (Dashboard, FormConfig, History)

### `src/lib/`
**Utility-Funktionen**:
- API-Client-Setup
- Helpers & Utils
- Konstanten

### `src/services/`
**Backend-Kommunikation**:
- API-Endpoints als Funktionen
- Error-Handling
- Request/Response-Mapping

### `src/types/`
**TypeScript Typen**:
- API Response Types
- Domain Types
- Enums

### `src/constants/`
**Statische Konfiguration**:
- `tasks.ts` - Task-Definitionen (Labels, Icons, Max-Punkte)
- `audio.ts` - Audio-Konstanten

## Kommunikation mit Backend

```
Frontend (Port 3000)
    ↓
API Services (src/services/)
    ↓
HTTP Requests
    ↓
Nginx Reverse Proxy (Port 80)
    ↓
Backend API (Port 8000)
```

Im Docker-Setup laeuft die Kommunikation ueber den Nginx Reverse Proxy (`http://localhost/api`).

## Entwicklungs-Workflow

1. **Feature entwickeln** in `src/components/` oder `src/app/`
2. **Typen definieren** in `src/types/`
3. **API-Calls** über `src/services/`
4. **Styles** mit Tailwind CSS
5. **Testen** im Dev-Server (`npm run dev`)

## Debugging

```bash
# Dev Server mit Debug-Output
npm run dev

# Komponenten-Fehler sehen im Browser
# -> http://localhost:3000
```

## Build & Deploy

```bash
# Production Build
npm run build

# Lokales Testen des Builds
npm start

# Docker Build
docker build -f ../docker/Dockerfile.frontend .
```
