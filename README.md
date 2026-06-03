# neurospeech-pipeline

A containerized system for AI-assisted speech analysis.

> ⚠️ **Research prototype — not a medical device.** Provided for research and reproducibility only; not
> validated or certified for clinical or diagnostic use. The repository is under active development; the
> version accompanying the publication is the tagged snapshot / Zenodo DOI in [Citation](#citation) and
> may differ from `main`. A commercial product may emerge from this project.

## Overview

neurospeech-pipeline is a web application for recording, transcribing, and analysing speech samples. It
combines OpenAI Whisper (`large-v3`) for speech recognition, GPT-4o / GPT-4o-mini for content scoring, and
spaCy (`de_core_news_lg`) for linguistic metrics, optimised for German. Three elicitation tasks are
supported — semantic verbal fluency (vegetables), proverb explanation, and picture description — and results
are stored in an i2b2 star schema with HL7 FHIR R4 export/import.

## Features

- **Transcription & linguistic analysis** — Whisper ASR → spaCy metrics (part-of-speech, type–token ratio, sentence length) → GPT-based semantic content scoring.
- **Acoustic voice features** — Praat/parselmouth (jitter, shimmer, MFCC-13, HNR, F0) with an age-/sex-matched Bayesian voice score (closed-form Normal-Inverse-Gamma).
- **Clinical interoperability** — i2b2 star schema (EAV) storage and HL7 FHIR R4 export/import (Patient, DiagnosticReport, Observation).
- **Demo data** — one-click loader for the public MDVR-KCL dataset (37 recordings; Zenodo).
- **Security** — JWT authentication, dual-database design, per-user encrypted OpenAI keys.
- **Deployment** — fully containerized (Docker Compose + Nginx).

## Architecture

```
Dev:  3 containers           Prod: 2 containers (no frontend container)

┌─────────────────┐    ┌──────────────┐    ┌──────────────────┐
│   Frontend      │    │    Nginx     │    │    Backend       │
│   (Next.js)     │<──>│  (reverse    │<──>│   (FastAPI)      │
│   dev only      │    │   proxy)     │    │   port 8000      │
└─────────────────┘    │  port 8088   │    └──────────────────┘
                       │  prod: ./www │             │
                       └──────────────┘   ┌─────────┴─────────┐
                                   ┌──────────────┐  ┌──────────────┐
                                   │  speech1.db  │  │  users.db    │
                                   │  (measure-   │  │  (users &    │
                                   │   ments)     │  │  API keys)   │
                                   └──────────────┘  └──────────────┘
                                          appdata/
```

## Tech stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, SQLAlchemy, Python 3.11+ |
| AI/ML | Whisper `large-v3`, GPT-4o / GPT-4o-mini, spaCy `de_core_news_lg` |
| Acoustics | praat-parselmouth, numpy, pydub |
| Interoperability | HL7 FHIR R4; i2b2 star schema (SQLite) |
| Infrastructure | Docker Compose, Nginx |

## Quick start

```bash
git clone https://github.com/BIOMAGuser/neurospeech-pipeline.git
cd neurospeech-pipeline
cp .env.example .env          # set JWT_SECRET_KEY and admin credentials
./docker-start.sh             # Linux/macOS · Windows: docker-start.bat / .ps1
```

Then open **http://localhost:8088** (interactive API docs at `/api/docs`). The OpenAI key is set per user in
the app settings. Use `--dev` for hot-reload, `--prod` (default) for the static build, `--build` to rebuild,
and `--stop` to stop. An admin user (from `.env`) and a standard clinical user are seeded on first start.

## Configuration

Key `.env` variables:

```bash
JWT_SECRET_KEY=<min. 32 chars>   # python3 -c "import secrets; print(secrets.token_hex(32))"
ADMIN_USERNAME=...
ADMIN_PASSWORD=...
```

Model and prompt settings live in `backend/config/prompts.yml` and can be changed without touching code.

## API

All backend routes are served under `/api` (e.g. `http://localhost:8088/api/analyze`); interactive
documentation is available at `http://localhost:8088/api/docs`. Endpoints cover analysis
(`/analyze`, `/analyze_text`), acoustic features (`/trials/{id}/acoustic`, `/acoustic/…`), FHIR
export/import (`/export`, `/import/…`), and user/key management.

## Data availability

This repository contains **no patient data**. The speech recordings and individual clinical data analysed in
the accompanying publication are not publicly available (data protection and ethics); de-identified data are
available from the corresponding author on reasonable request. A loader for the public **MDVR-KCL** dataset
(Zenodo; 16 Parkinson's + 21 control recordings) is included for demonstration and reproduction.

## Citation

If you use this software, please cite the article and the archived snapshot:

- Justi L, Uhlemann L, Mühlhammer H, Wieczorek B, Brodoehl S. *Development and Validation of an End-to-End
  Automated Speech Analysis Pipeline in Parkinson's Disease: Transcription, Linguistic Feature Extraction,
  and Semantic Scoring versus Manual Analysis.* [Journal], [year]. DOI: [article DOI]
- Software snapshot: Zenodo, DOI: 10.5281/zenodo.XXXXXXX

See `CITATION.cff`.

## License

Released under the **GNU Affero General Public License v3.0 (AGPL-3.0)** — see `LICENSE`. For commercial
licensing or uses beyond AGPL-3.0, please contact the authors or the Jena University Hospital technology
transfer office.

Copyright © Jena University Hospital (Universitätsklinikum Jena) and the authors.

## Contact

Developed at Jena University Hospital. Contact: S. Brodoehl and L. Justi
(corresponding author: lydia.justi@med.uni-jena.de).
