# SpeechScribe

Ein containerisiertes System zur neuropsychologischen Sprachanalyse mit KI-Integration.

## Ueberblick

SpeechScribe ist eine Webanwendung zur Aufnahme, Transkription und KI-gestuetzten Analyse von Sprachproben. Das System nutzt OpenAI Whisper fuer Spracherkennung, GPT fuer Textanalyse und spaCy fuer NLP-basierte Metriken. Optimiert fuer deutsche Sprache.

### Hauptfunktionen

- **Audio-Transkription**: Automatische Umwandlung von Sprache zu Text mit Whisper
- **KI-Textanalyse**: Intelligente Analyse von Inhalten mit GPT-4-turbo
- **NLP-Metriken**: Wortarten-Analyse, TTR, Satzlaenge mit spaCy
- **Akustische Stimm-Features**: On-demand Berechnung von Jitter, Shimmer, MFCC-13, HNR und F0-Statistik via Praat (parselmouth) — 39 Messwerte pro Trial
- **AcousticLab**: Frontend-Tab mit Bulk-Trigger und Bayesian-Score (PD_Voice_Age_Score) gegen alters-/geschlechts-gematchte Kontrollkohorte — closed-form Normal-Inverse-Gamma, wächst inkrementell mit jeder neuen Messung
- **MDVR-KCL Demo-Loader**: Ein-Klick-Import von 37 Sprachaufnahmen (16 Parkinson + 21 Kontrolle) aus dem öffentlichen Zenodo-Datensatz — Live-Streaming-Progress, idempotent, mit Bulk-Delete
- **Drei Aufgabentypen**: Gemuese (semantische Fluenz), Sprichwort, Bildbeschreibung
- **i2b2 Star Schema**: Klinikkonforme EAV-Speicherung (`OBSERVATION_FACT`/`PATIENT_DIMENSION`/`VISIT_DIMENSION`/`CONCEPT_DIMENSION`)
- **HL7 FHIR R4 Export/Import**: Standardisierter Datenaustausch via FHIR Bundle (Patient, DiagnosticReport, Observation)
- **Export-Status-Tracking**: Visuelle Indikatoren (gruen/orange/rot) zeigen Export-Status pro Patient und Analyse
- **Benutzerauthentifizierung**: JWT-basiertes Login mit Dual-DB Architektur
- **Per-User API-Keys**: Verschluesselte OpenAI-Key Verwaltung pro Benutzer
- **Docker-Integration**: Vollstaendig containerisierte Architektur

## Architektur

```
Dev:  3 Container            Prod: 2 Container (kein Frontend-Container)

┌─────────────────┐    ┌──────────────┐    ┌──────────────────┐
│   Frontend      │    │    Nginx     │    │    Backend       │
│   (Next.js)     │<──>│  (Reverse    │<──>│   (FastAPI)      │
│   nur Dev-Modus │    │   Proxy)     │    │   Port: 8000     │
└─────────────────┘    │  Port: 8088  │    └──────────────────┘
                       │  Prod: ./www │             │
                       └──────────────┘   ┌─────────┴─────────┐
                                          │                   │
                                   ┌──────────────┐  ┌──────────────┐
                                   │  speech1.db  │  │  users.db    │
                                   │  Messdaten   │  │  Nutzer &    │
                                   │              │  │  API-Keys    │
                                   └──────────────┘  └──────────────┘
                                          appdata/
```

### Dual-DB Architektur

| Datenbank | Inhalt |
|-----------|--------|
| `appdata/speech1.db` | Patienten, Analysen, Trials (Messdaten) |
| `appdata/users.db` | Benutzer, Einstellungen, verschluesselte API-Keys |

## Technologie-Stack

| Layer | Technologien |
|-------|--------------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| **Backend** | FastAPI, SQLAlchemy, Python 3.11+, spaCy |
| **AI/ML** | OpenAI Whisper (STT), GPT-4-turbo (Analyse), spaCy (NLP) |
| **Akustik** | praat-parselmouth (Praat 6.x), numpy, pydub |
| **Statistik** | scipy (Student-t), numpy — closed-form Normal-Inverse-Gamma |
| **Datenaustausch** | HL7 FHIR R4 (DiagnosticReport, Observation, Patient) |
| **Datenbank** | SQLite, i2b2 Star Schema (Dual-DB) |
| **Infrastruktur** | Docker Compose, Nginx, Backend `linux/amd64` (parselmouth-Wheel) |

## Quick Start

### Voraussetzungen

- Docker und Docker Compose (v2)
- OpenAI API-Schluessel (wird pro User in der App unter Einstellungen gesetzt)

### 1. Repository klonen

```bash
git clone https://github.com/stebro01/SpeechScribe.git
cd SpeechScribe
```

### 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# .env bearbeiten und Werte eintragen
```

### 3. Docker Container starten

```bash
# Linux / macOS
chmod +x docker-start.sh
./docker-start.sh

# Windows (CMD)
docker-start.bat

# Windows (PowerShell)
.\docker-start.ps1
```

Optionen fuer alle Start-Skripte:

| Option | Beschreibung |
|--------|--------------|
| `--dev` / `-Mode dev` | Dev-Umgebung (HMR, Live-Reload) |
| `--prod` / `-Mode prod` | Production Build (default) |
| `--build` / `-Build` | Docker-Images vor dem Start neu bauen |
| `--stop` / `-Stop` | Alle Services stoppen |
| `--help` / `-Help` | Optionen anzeigen |

Oder direkt mit Docker Compose:

```bash
docker compose up -d                                        # Prod (default, braucht ./www)
docker compose --profile dev up -d backend frontend nginx   # Dev (HMR)
```

### 4. Anwendung oeffnen

```
http://localhost:8088
```

Beide Modi (Dev und Prod) laufen auf Port 8088 — immer nur einer gleichzeitig.

### Benutzer

Beim ersten Start werden zwei Benutzer automatisch angelegt:

| Benutzer | Passwort | Beschreibung |
|----------|----------|--------------|
| `testuser` | `testpassword` | Admin (aus .env ADMIN_USERNAME/PASSWORD) |
| `arzt` | `arzt1234` | Standard-Benutzer fuer klinische Nutzung |

## Ordnerstruktur

```
SpeechScribe/
├── backend/                    # FastAPI Backend
│   ├── main.py                 # Entry Point, Lifespan, DB-Migrationen
│   ├── config.py               # Pydantic Settings (env vars)
│   ├── config/                 # YAML-Konfigurationsdateien
│   │   ├── prompts.yml         # OpenAI Prompt-Konfiguration
│   │   ├── form_config.yml     # Patientenformular-Felder
│   │   └── fhir_export_template.yml  # FHIR R4 Mapping-Spezifikation
│   ├── routers/                # API Router (auth, analysis, acoustic, status, data, users, config)
│   ├── analysis/               # Sprachanalyse-Module (veggie, saying, picture, acoustic, bayesian)
│   ├── service/                # Auth, FHIR, Whisper, GPT, Encryption, Key-Service, observation_builder, trial_serializer, cohort_stats
│   ├── db/                     # i2b2 Star-Schema Modelle, Repositories, Migrationen, Seeds
│   │   ├── models_star.py      # i2b2-Tabellen (PATIENT_DIMENSION, VISIT_DIMENSION, OBSERVATION_FACT, ...)
│   │   ├── repositories/       # patient/visit/observation/concept Repositories
│   │   ├── migrations/         # v001…v006 (registriert in migration_manager.py)
│   │   └── seeds/concepts.py   # SS:* Concept-Vokabular (inkl. SS:ACOUSTIC:*)
│   └── tests/                  # Integration Tests (93 Tests)
├── frontend/                   # Next.js Frontend
│   └── src/
│       ├── app/                # Pages & Routes (login, measurement, history, admin)
│       ├── components/         # React Components
│       ├── services/           # API Services (auth, dashboard, audio-analysis, history)
│       ├── hooks/              # Custom React Hooks
│       ├── types/              # TypeScript Types
│       └── lib/                # Utilities (api.ts, audio-utils.ts)
├── docker/                     # Docker Konfiguration
│   ├── Dockerfile.backend      # Backend Image
│   ├── Dockerfile.frontend     # Frontend Image (Multi-Stage: dev + runner)
│   ├── nginx.dev.conf          # Nginx Config Dev (Proxy zu Frontend Container)
│   ├── nginx.prod.conf         # Nginx Config Prod (serviert ./www statisch)
│   └── nginx.conf              # Basis-Nginx-Config (Referenz)
├── docker-compose.yml          # Service-Orchestrierung (Dev/Prod umschaltbar)
├── docker-start.sh             # Start-Skript (Linux/macOS)
├── docker-start.bat            # Start-Skript (Windows CMD)
├── docker-start.ps1            # Start-Skript (Windows PowerShell)
├── .env                        # Umgebungsvariablen (nicht in Git)
├── .env.example                # Vorlage fuer .env
├── www/                        # Frontend Build-Output (nicht in Git, von --prod erzeugt)
├── appdata/                    # Laufzeitdaten (speech1.db, users.db, Logs, MP3s)
└── analysis_results/           # Forschungs-Ergebnisse
    └── acoustic/               # Beispiel-JSONs aus /trials/{id}/acoustic
```

## Umgebungsvariablen (.env)

```bash
# Erforderlich
JWT_SECRET_KEY=<min 32 Zeichen>      # JWT Signatur-Schluessel
# Generieren mit: python3 -c "import secrets; print(secrets.token_hex(32))"

# Admin-Benutzer (wird beim ersten Start angelegt)
ADMIN_USERNAME=testuser
ADMIN_PASSWORD=testpassword

# Optional - Separater Verschluesselungs-Key (Fallback: JWT_SECRET_KEY)
ENCRYPTION_KEY=

# Optional - OpenAI API Key fuer Integration Tests
TEST_OPENAI_API_KEY=

# Optional - Frontend URL fuer CORS (leer = nur Default-Origins)
FRONTEND_URL=

# Optional - Test-Login-Button auf Login-Seite (default: true, fuer Produktion auf false)
DEV_AUTOLOGIN=true

# Optional - Logging
LOG_RETENTION_DAYS=30
LOG_CLEANUP_ENABLED=true

# App Info
APP_NAME=PARK_SPEECH
APP_VERSION=3.1.0
BUILD_DATE=2026-03-28
```

## Services & Ports

Alle Modi laufen auf **Port 8088**. Nur ein Modus gleichzeitig.

| Service | Port | Beschreibung |
|---------|------|--------------|
| **Nginx** | 8088 | Reverse Proxy (extern erreichbar) |
| **Frontend Dev** | 3000 | Next.js Dev Server (nur mit --dev) |
| **Frontend Prod** | - | Statische Dateien in ./www (kein Container) |
| **Backend** | 8000 | FastAPI Server (intern) |
| **API Docs** | - | http://localhost:8088/api/docs |

## API Endpunkte

| Methode | Pfad | Beschreibung | Auth |
|---------|------|--------------|------|
| POST | `/token` | Login, gibt JWT zurueck | Nein |
| POST | `/analyze` | Audio hochladen, transkribieren & analysieren | Ja |
| POST | `/analyze_text` | Text direkt analysieren | Ja |
| GET | `/health` | Health-Check | Nein |
| GET | `/stats` | DB-Statistiken | Ja |
| GET | `/openai-status` | OpenAI-Verbindung pruefen | Ja |
| GET | `/config/client` | Client-Konfiguration (dev_autologin, app_name) | Nein |
| GET | `/config/patient-form` | Patientenformular-Felder (YAML) | Nein |
| GET | `/patients` | Patientenliste (mit export_status) | Ja |
| GET | `/patients/{id}/analyses` | Analysen eines Patienten (mit exported_at) | Ja |
| GET | `/analyses/{id}` | Analyse-Details mit Trials | Ja |
| GET | `/patients/{id}/export` | Patient als FHIR Bundle exportieren | Ja |
| GET | `/analyses/{id}/export` | Analyse als FHIR Bundle exportieren | Ja |
| GET | `/export` | Gesamte DB als FHIR Bundle | Ja |
| POST | `/import/patient` | FHIR Bundle importieren (Patient + Analysen) | Ja |
| POST | `/import/analysis` | FHIR Bundle importieren (einzelne Analyse) | Ja |
| DELETE | `/patients/{id}` | Patient loeschen (Cascade) | Ja |
| DELETE | `/analyses/{id}` | Analyse loeschen | Ja |
| GET | `/user/me` | Benutzer-Profil | Ja |
| PUT | `/user/openai-key` | OpenAI-Key speichern (verschluesselt) | Ja |
| GET | `/user/openai-key/status` | Hat User einen Key? | Ja |
| DELETE | `/user/openai-key` | Gespeicherten Key loeschen | Ja |
| GET | `/trials/{id}/audio` | MP3-Audio eines Trials streamen | Ja |
| POST | `/trials/{id}/acoustic` | Akustik-Features berechnen (Jitter/Shimmer/MFCC/HNR/F0) | Ja |
| GET | `/trials/{id}/acoustic` | Berechnete Akustik-Features lesen | Ja |
| GET | `/trials/{id}/acoustic/score` | PD_Voice_Age_Score + Per-Feature-Percentile | Ja |
| GET | `/acoustic/trials` | Liste aller Audio-Trials mit Status | Ja |
| GET | `/acoustic/cohort` | Referenzkohorten-Übersicht | Ja |
| GET | `/acoustic/samples/status` | MDVR-KCL Cache + n_imported | Ja |
| POST | `/acoustic/samples/load` | Stream-Loader Zenodo → DB (ndjson) | Ja |
| DELETE | `/acoustic/samples` | Alle `DEMO-MDVR-*` Patienten + MP3s entfernen | Ja |
| GET | `/version` | App-Version und Build-Info | Nein |
| GET | `/users` | Benutzerliste (nur Admin) | Ja |
| POST | `/users` | Benutzer erstellen (nur Admin) | Ja |
| PUT | `/users/{id}` | Benutzer aktualisieren (nur Admin) | Ja |
| DELETE | `/users/{id}` | Benutzer loeschen (nur Admin) | Ja |

Via Nginx: alle Backend-Routen unter `/api` (z.B. `http://localhost:8088/api/analyze`)

## FHIR R4 Export/Import

Export und Import verwenden das HL7 FHIR R4 Bundle-Format:

| SpeechScribe | FHIR Ressource | Beschreibung |
|---|---|---|
| Patient | `Patient` | Identifier, Gender, BirthDate |
| Analysis | `DiagnosticReport` | Status, Date, MoCA (Extension), Group (Extension), Notes |
| Trial | `Observation` | Task-Code, Transcript, Metriken als Components |

Das Mapping ist in `backend/config/fhir_export_template.yml` definiert. Dedup erfolgt ueber `session_analysis_id`.

## OpenAI Konfiguration

Alle Prompts und Modell-Einstellungen sind zentral in `backend/config/prompts.yml` konfiguriert:

- **Whisper**: Modell, Sprache, Temperatur, Task-spezifische Prompts
- **GPT**: Modell, Temperatur, Max-Tokens, Analyse-Prompts (Veggie, Saying, Refine)

Aenderungen an Prompts erfordern keinen Code-Umbau — nur die YAML-Datei bearbeiten.

## Entwicklung

Die gesamte Entwicklung laeuft ueber Docker. Es gibt keine lokale Installation.

### Dev-Modus (HMR, Live-Reload)

```bash
./docker-start.sh --dev          # oder: docker compose --profile dev up -d

# Logs
docker compose logs -f
docker compose logs -f frontend

# Stoppen
./docker-start.sh --stop         # oder: docker compose down
```

Im Dev-Modus wird der Frontend-Quellcode als Volume gemountet. Aenderungen an Dateien in `frontend/src/` werden sofort im Browser sichtbar (HMR via Next.js Turbopack).

### Prod-Modus (default, statischer Build)

```bash
./docker-start.sh --prod         # oder: docker compose up -d
```

Der Prod-Build kompiliert das Frontend zu statischen HTML/JS/CSS-Dateien in `./www/`.
Nginx serviert diese direkt — **kein Frontend-Container noetig**. Dies ist der Default-Modus.

### App neu bauen (Rebuild)

```bash
# Frontend neu bauen und starten
./docker-start.sh --prod --build

# Nur Backend neu bauen
docker compose up --build -d backend

# Kompletter Clean-Rebuild (inkl. node_modules)
docker compose down
docker volume rm speechscribe_frontend_node_modules
rm -rf www
./docker-start.sh --build
```

Der Build-Output liegt in `./www/` (statische HTML/JS/CSS-Dateien).
Beim ersten `--prod` Start oder mit `--build` wird automatisch gebaut.

### Nuetzliche Befehle

```bash
# Container-Status
docker compose ps

# In Container-Shell einsteigen
docker compose exec backend bash
docker compose exec frontend sh
```

## Integration Tests

105 Tests decken die gesamte Pipeline ab: Auth, Key-Management, Textanalyse, Audio-Pipeline, akustische Features, AcousticLab/Bayesian-Scoring, Transaction-Safety, User-Management, Datenisolation, FHIR Export/Import, Config-Endpoints und i2b2 Star-Schema.

```bash
# Direkt im Backend-Container ausfuehren (pytest einmalig nachinstallieren)
docker compose exec backend pip install --quiet pytest requests
docker compose exec backend python -m pytest tests/ -v --tb=short
```

| Suite | Tests | Braucht OpenAI Key |
|-------|-------|--------------------|
| Health/Status (`test_01`) | 5 | Nein |
| Auth & Login (`test_02`) | 7 | Nein |
| OpenAI Key CRUD (`test_03`) | 6 | Nein |
| Text-Analyse (`test_04`) | 4 | Veggie/Saying: Ja, Picture: Nein |
| Audio-Pipeline (`test_05`) | 5 | Ja (Whisper) |
| Transaction-Safety (`test_06`) | 4 | Nein |
| User-Management (`test_07`) | 20 | Nein |
| Datenisolation (`test_08`) | 8 | Nein |
| FHIR Export/Import (`test_09`) | 20 | Nein |
| Acoustic Features (`test_10_acoustic`) | 5 | Smoke-Tests brauchen Trial mit Audio (also `test_05`) |
| Star Schema (`test_10_star_schema`) | 9 | Nein |
| AcousticLab + Bayesian (`test_11_acousticlab`) | 12 | Smoke-Test für `/score` braucht Trial mit Acoustic-Features |

**Hinweis:** Tests die GPT oder Whisper nutzen werden automatisch uebersprungen wenn kein gueltiger OpenAI-Key konfiguriert ist.

## Troubleshooting

### Container starten nicht
```bash
docker compose logs
docker compose ps
docker compose down && docker compose up --build
```

### Port bereits belegt
```bash
lsof -i :8088
```

### Datenbank zuruecksetzen
```bash
# Messdaten zuruecksetzen (Patienten, Analysen, Trials)
rm appdata/speech1.db
docker compose restart backend

# Benutzer zuruecksetzen (werden neu geseeded)
rm appdata/users.db
docker compose restart backend
```

## Dokumentation

| Bereich | Datei |
|---------|-------|
| Ordnerstruktur | [FOLDER_STRUCTURE.md](FOLDER_STRUCTURE.md) |
| Claude / AI Agent Referenz | [CLAUDE.md](CLAUDE.md) |
| Frontend | [frontend/README.md](frontend/README.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| API Docs | http://localhost:8088/api/docs |
