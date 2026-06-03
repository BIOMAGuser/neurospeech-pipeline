# SpeechScribe Ordnerstruktur

## APP (Production)
```
backend/                    # FastAPI Backend
frontend/                   # Next.js Frontend
docker/                     # Dockerfiles & Nginx Config
appdata/                    # Datenbanken, Logs & Audio (runtime)
  speech1.db                # Messdaten (i2b2 Star Schema)
  users.db                  # Benutzer, Einstellungen, verschluesselte API-Keys
  logs/                     # Log-Dateien (app.log, error.log — taegliche Rotation)
  mp3/                      # Gespeicherte Audio-Aufnahmen (UUID-basiert)
docker-compose.yml          # Service-Orchestrierung (Dev/Prod, Backend auf linux/amd64)
.env                        # Umgebungsvariablen (nicht in Git)
.env.example                # Vorlage fuer .env
CLAUDE.md                   # Claude / AI Agent Referenz
```

## Docker
```
docker/
├── Dockerfile.backend      # Python 3.11-slim Image
├── Dockerfile.frontend     # Node 18-Alpine Multi-Stage (dev + runner Targets)
├── nginx.conf              # Reverse Proxy (Produktion: Gzip, Rate-Limiting, Security)
└── nginx.dev.conf          # Reverse Proxy (Entwicklung: HMR-Timeouts, kein Rate-Limiting)
```

## Backend
```
backend/
├── main.py                 # FastAPI Entry Point, Lifespan (DB-Init, Migrations, User-Seed)
├── config.py               # Pydantic Settings (env vars inkl. DEV_AUTOLOGIN)
├── prompt_config.py        # YAML-Loader (whisper_cfg, gpt_cfg)
├── form_config.py          # YAML-Loader fuer Formular-Config
├── version.py              # Version-Endpoint Daten
├── requirements.txt        # Python Dependencies
├── config/                 # Zentrale YAML-Konfiguration
│   ├── prompts.yml         # OpenAI Prompt- & Modell-Konfiguration
│   ├── form_config.yml     # Patientenformular (Felder, Optionen, Validierung)
│   └── fhir_export_template.yml  # HL7 FHIR R4 Mapping-Spezifikation
├── routers/                # API Router
│   ├── auth.py             # Login, User-Profil, OpenAI-Key Verwaltung
│   ├── analysis.py         # Audio-Analyse & Text-Analyse Endpunkte
│   ├── acoustic.py         # POST/GET /trials/{id}/acoustic
│   ├── status.py           # Health, Stats, OpenAI-Status
│   ├── data.py             # Patienten, Analysen, FHIR Export/Import
│   ├── users.py            # User-Management CRUD (Admin-only)
│   ├── form_config.py      # GET /config/patient-form, GET /config/client
│   ├── debug.py            # Debug-Endpunkte (nur bei DEBUG=true)
│   └── version.py          # GET /version App-Version & Build-Info
├── analysis/               # Sprachanalyse-Module
│   ├── task_registry.py    # Zentrale Task-Definitionen (Analyse, Scoring, Max-Punkte)
│   ├── analyse_veggie.py   # Semantische Fluenz (Gemuese) — GPT
│   ├── analyse_saying.py   # Sprichwort-Verstaendnis — GPT
│   ├── analyse_picture.py  # Bildbeschreibung (Cookie Theft) — NLP only
│   ├── acoustic.py         # Akustische Features (Jitter/Shimmer/MFCC/HNR/F0) via parselmouth
│   ├── bayesian.py         # NIG-Posterior + Student-t Predictive + voice_age_score
│   ├── constants.py        # Fuellwoerter-Liste
│   ├── nlp.py              # spaCy Model Loader
│   └── whisper_word_count.py # Rohwort-Zaehlung
├── middleware/              # HTTP Middleware
│   └── logging_middleware.py # Request-Logging, Request-ID Tracking, JWT User-Extraktion
├── service/                # Business Logic
│   ├── auth_service.py     # JWT Auth, User-CRUD (users.db)
│   ├── fhir_service.py     # FHIR R4 Bundle Export/Import (YAML-gesteuert)
│   ├── whisper_service.py  # OpenAI Whisper (Speech-to-Text)
│   ├── gpt_service.py      # GPT Chat Completion
│   ├── encryption_service.py # Fernet Ver-/Entschluesselung (API-Keys)
│   ├── openai_key_service.py # Key-Aufloesung (User-DB, kein env Fallback)
│   ├── audio_storage_service.py # MP3-Konvertierung, Speicherung & Cleanup
│   ├── observation_builder.py   # Star-Schema Schreib-Orchestration (Patient/Visit/OBS)
│   ├── trial_serializer.py      # Star-Schema -> legacy API dict (compat layer)
│   ├── cohort_stats.py          # NIG-Posteriors per Zelle, Score-Berechnung, Trial-Listing
│   └── sample_loader.py         # MDVR-KCL Zenodo-Stream, Extract, Demo-Patient-Import
├── db/                     # Datenbank (i2b2 Star Schema)
│   ├── database.py         # Dual-DB: engine + user_engine, SessionLocal + UserSessionLocal
│   ├── models_star.py      # i2b2-Modelle (PATIENT_DIMENSION, VISIT_DIMENSION, OBSERVATION_FACT, CONCEPT_DIMENSION + 9 Lookup-Tabellen)
│   ├── models.py           # Re-Export-Shim fuer Backward-Compat-Imports
│   ├── user_models.py      # User-DB Modelle (User, Setting)
│   ├── init_db.py          # DB-Initialisierung
│   ├── views.py            # SQL Views
│   ├── repositories/       # Repositories: patient, visit, observation, concept (+ base)
│   ├── seeds/concepts.py   # SS:* Concept-Vokabular inkl. SS:ACOUSTIC:*
│   └── migrations/         # v001 create_star_schema, v002 seed_concepts, v003 views,
│                           # v004 migrate_historical_data, v005 drop_legacy_tables,
│                           # v006 seed_acoustic_concepts (registriert in migration_manager.py)
└── tests/                  # Integration Tests (93 Tests)
    ├── conftest.py         # Pytest Fixtures (Auth-Tokens, Base-URL)
    ├── helpers.py          # Shared Test-Helfer
    ├── generate_audio_fixtures.py  # gTTS Audio-Generator
    ├── run_tests.sh        # Test-Runner Script
    ├── fixtures/           # Test-Daten
    │   ├── veggie_answer.txt/mp3
    │   ├── saying_answer.txt/mp3
    │   └── picture_answer.txt/mp3
    ├── test_01_health.py   # Health, Stats, Auth-Guards
    ├── test_02_auth.py     # Login, User-Profil
    ├── test_03_openai_key.py # Key CRUD Lifecycle
    ├── test_04_text_analysis.py # Alle 3 Aufgaben via /analyze_text
    ├── test_05_audio_pipeline.py # Whisper→GPT→Star Schema Pipeline
    ├── test_06_transaction_safety.py # Rollback, Views
    ├── test_07_user_management.py # User-CRUD, Admin-Rechte
    ├── test_08_data_isolation.py # Multi-User Datenisolation
    ├── test_09_export_import.py # FHIR Export/Import, Status-Tracking, Config
    ├── test_10_acoustic.py # POST/GET /trials/{id}/acoustic (Praat-Features)
    ├── test_10_star_schema.py # i2b2 EAV-Roundtrip, Edge-Cases
    └── test_11_acousticlab.py # Bayesian-Math + AcousticLab-Endpoints (12 Tests)
```

## Frontend
```
frontend/
├── src/
│   ├── app/                # Next.js Pages & Routes
│   │   ├── login/          # Login-Seite (mit konfigurierbarem Test-Login)
│   │   └── (protected)/    # Auth-geschuetzte Seiten
│   │       ├── page.tsx    # Dashboard
│   │       ├── measurement/# Neue Messung (3-Step Wizard)
│   │       ├── acousticlab/# AcousticLab (Trial-Liste, Bulk-Trigger, Bayesian-Score)
│   │       ├── history/    # Patienten- & Analyse-Historie (mit Export-Status-Dots)
│   │       ├── settings/   # Benutzer-Einstellungen (OpenAI API-Key)
│   │       └── admin/      # Admin (Export, Stats, User-Verwaltung)
│   ├── components/         # React Components (+ shadcn/ui)
│   │   └── acousticlab/    # AcousticLabPage, List, Detail (Sheet), BulkProgress, SampleLoadModal
│   ├── constants/          # Statische Konfiguration
│   │   └── tasks.ts        # Task-Definitionen (Labels, Icons, Max-Punkte)
│   ├── services/           # API Service Layer
│   │   ├── auth.ts         # Login, Logout, Token-Verwaltung
│   │   ├── dashboard.ts    # Health, Stats, OpenAI-Status
│   │   ├── audio-analysis.ts # Audio-Upload & Analyse
│   │   ├── form-config.ts  # Patientenformular-Konfiguration vom Backend
│   │   └── history.ts      # Patienten, Analyse-Daten, FHIR Import/Export
│   ├── hooks/              # Custom React Hooks
│   │   └── queries/        # React-Query Hooks (use-dashboard, use-form-config, use-history)
│   ├── types/              # TypeScript Types
│   └── lib/                # Utilities (api.ts, audio-utils.ts)
├── package.json            # NPM Dependencies
├── next.config.ts          # Next.js Config (standalone output)
├── tailwind.config.ts      # Tailwind CSS Config
└── tsconfig.json           # TypeScript Config
```

## ANALYSIS (Forschung)
```
analysis_results/           # Analyse-Skripte, Visualisierungen, Ergebnisse
└── acoustic/               # Beispiel-JSONs aus POST /trials/{id}/acoustic
    ├── _summary.json       # Cross-Trial-Index
    └── trial_NNNN_<task>.json  # Pro Trial: 39-Feature-Block + Anker
```

## DOCS
```
docs/
└── lit/                    # Literatur (Methodik-Referenzen)
```

---
**Regel:**
- App-Ordner sind **notwendig** fuer den Betrieb
- Analysis-Ordner sind **optional** fuer Forschung & Publikation
