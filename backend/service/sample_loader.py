"""
On-demand loader for the public MDVR-KCL Parkinson voice dataset.

Downloads the Zenodo zip (DOI 10.5281/zenodo.2867216, CC-BY-4.0) on first
call, extracts it under appdata/samples/mdvr_kcl/, and imports each
relevant WAV file into the i2b2 star schema as a DEMO-MDVR-XX patient.

Demographics (age, gender) are not in the public MDVR-KCL filename scheme
— they are synthesized deterministically from the file id, with PD
patients biased toward 60-80 years old (typical onset) and HC controls
spanning 30-80. This is transparent demo data, marked with a DEMO-
prefix in PATIENT_CD.

Filename convention (per the original release):
    ID00_HC.wav                     # healthy control
    ID16_PD_H&Y2_UPDRSII4_UPDRSIII15.wav   # Parkinson's, with clinical scores
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

import httpx
from pydub import AudioSegment
from sqlalchemy.orm import Session

from db.models_star import (
    NoteFact,
    ObservationFact,
    PatientDimension,
    UserPatientLookup,
    VisitDimension,
)
from db.repositories.observation_repository import (
    AUDIO_DURATION_CONCEPTS,
    ObservationRepository,
)
from db.repositories.patient_repository import PatientRepository
from db.repositories.visit_repository import VisitRepository
from db.seeds.concepts import GENDER_TO_SNOMED
from service.audio_storage_service import convert_and_save_mp3

logger = logging.getLogger(__name__)


# ── Constants ───────────────────────────────────────────────

ZENODO_ZIP_URL = (
    "https://zenodo.org/records/2867216/files/26_29_09_2017_KCL.zip"
)
DEMO_PATIENT_PREFIX = "DEMO-MDVR-"
SOURCE_TAG = "MDVR-KCL"
DEMO_TASK = "voicesample"  # dedicated category for acoustic-only audio
DEMO_NOTE = (
    "Demo sample from MDVR-KCL (Jaeger et al., King's College London, "
    "Zenodo DOI 10.5281/zenodo.2867216, CC-BY-4.0). Demographics are "
    "synthesized for cohort demonstration."
)


def _appdata_dir() -> Path:
    from config import settings
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    return Path(db_path).parent


def _samples_root() -> Path:
    root = _appdata_dir() / "samples" / "mdvr_kcl"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _zip_path() -> Path:
    return _samples_root() / "mdvr_kcl.zip"


def _extracted_dir() -> Path:
    return _samples_root() / "extracted"


# ── Filename parsing ────────────────────────────────────────

_FNAME_RE = re.compile(
    r"ID(?P<id>\d+)_"
    r"(?P<group>HC|PD)"
    r"(?:_H&?Y(?P<hy>\d+))?"
    r"(?:_UPDRSII(?P<u2>\d+))?"
    r"(?:_UPDRSIII(?P<u3>\d+))?"
    r".*\.wav$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SampleMeta:
    file_id: str         # "ID16"
    raw_name: str        # actual filename
    group: str           # "Kontrolle" | "Parkinson"
    hy_stage: Optional[int]
    updrs_ii: Optional[int]
    updrs_iii: Optional[int]
    abs_path: Path


def _parse_filename(path: Path) -> Optional[SampleMeta]:
    m = _FNAME_RE.search(path.name)
    if not m:
        return None
    raw_group = m.group("group").upper()
    group = "Parkinson" if raw_group == "PD" else "Kontrolle"
    return SampleMeta(
        file_id=f"ID{m.group('id')}",
        raw_name=path.name,
        group=group,
        hy_stage=int(m.group("hy")) if m.group("hy") else None,
        updrs_ii=int(m.group("u2")) if m.group("u2") else None,
        updrs_iii=int(m.group("u3")) if m.group("u3") else None,
        abs_path=path,
    )


# ── Demographic synthesis ───────────────────────────────────

def _seeded(file_id: str, salt: str) -> int:
    """Deterministic per-(file_id, salt) integer in [0, 2**32)."""
    h = hashlib.sha256(f"{file_id}|{salt}".encode()).digest()
    return int.from_bytes(h[:4], "big")


def _synth_gender(file_id: str) -> str:
    return "m" if _seeded(file_id, "gender") % 2 == 0 else "f"


def _synth_birth_date(file_id: str, group: str, ref_year: int = 2017) -> str:
    """
    Synthesize a plausible birth date for the demo patient.
    PD patients: ages 55-85 (median ~67). HC: ages 30-75 (uniform).
    Year-of-recording is 2017 (when MDVR-KCL was collected).
    """
    if group == "Parkinson":
        # Triangular distribution centered around 67
        r = _seeded(file_id, "age") % 31  # 0..30
        age = 55 + r
    else:
        r = _seeded(file_id, "age") % 46  # 0..45
        age = 30 + r
    birth_year = ref_year - age
    month = (_seeded(file_id, "month") % 12) + 1
    day = (_seeded(file_id, "day") % 28) + 1
    return f"{birth_year:04d}-{month:02d}-{day:02d}"


# ── Download ────────────────────────────────────────────────

def is_downloaded() -> bool:
    return _zip_path().exists() and _zip_path().stat().st_size > 100_000_000


def is_extracted() -> bool:
    if not _extracted_dir().exists():
        return False
    # require at least one .wav under extracted/
    return any(_extracted_dir().rglob("*.wav"))


def stream_download(chunk_mb: int = 1) -> Iterator[dict]:
    """
    Stream the Zenodo zip. Yields dicts with progress info per chunk.
    Idempotent: skips if already cached.
    """
    target = _zip_path()
    if is_downloaded():
        yield {"phase": "download", "status": "cached", "bytes": target.stat().st_size}
        return

    # Stream into a temp file, rename when finished
    tmp = target.with_suffix(".part")
    if tmp.exists():
        tmp.unlink()

    chunk_bytes = chunk_mb * 1_048_576
    yield {"phase": "download", "status": "starting", "url": ZENODO_ZIP_URL}

    with httpx.stream("GET", ZENODO_ZIP_URL, follow_redirects=True, timeout=None) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with tmp.open("wb") as f:
            for chunk in resp.iter_bytes(chunk_size=chunk_bytes):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                yield {
                    "phase": "download",
                    "status": "progress",
                    "downloaded_mb": round(downloaded / 1_048_576, 1),
                    "total_mb": round(total / 1_048_576, 1) if total else None,
                    "pct": round(100 * downloaded / total, 1) if total else None,
                }
    tmp.rename(target)
    yield {"phase": "download", "status": "done", "bytes": target.stat().st_size}


def extract_zip() -> list[Path]:
    """Extract the cached zip into appdata/samples/mdvr_kcl/extracted/ and return wavs."""
    out = _extracted_dir()
    if is_extracted():
        return sorted(out.rglob("*.wav"))
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(_zip_path(), "r") as zf:
        zf.extractall(out)
    return sorted(out.rglob("*.wav"))


# ── Import into star schema ─────────────────────────────────

def _backfill_demo_duration(
    db: Session,
    patient_num: int,
    meta: SampleMeta,
    duration_cd: str,
) -> None:
    """Add SS:PICTURE:AUDIO_DURATION for a previously-imported demo trial that lacks it."""
    existing = (
        db.query(ObservationFact)
        .filter(
            ObservationFact.PATIENT_NUM == patient_num,
            ObservationFact.CONCEPT_CD == duration_cd,
        )
        .first()
    )
    if existing is not None:
        return
    # Find the trial encounter (the one that holds the audio_uuid)
    visit = (
        db.query(VisitDimension)
        .filter(VisitDimension.PATIENT_NUM == patient_num)
        .order_by(VisitDimension.ENCOUNTER_NUM)
        .first()
    )
    if visit is None:
        return
    try:
        duration = AudioSegment.from_file(meta.abs_path).duration_seconds
    except Exception:
        return
    if not duration or duration <= 0:
        return
    now = datetime.now().isoformat()
    db.add(ObservationFact(
        ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
        PATIENT_NUM=patient_num,
        CONCEPT_CD=duration_cd,
        CATEGORY_CHAR=DEMO_TASK,
        PROVIDER_ID=meta.file_id,
        START_DATE=now,
        INSTANCE_NUM=1,
        VALTYPE_CD="N",
        NVAL_NUM=float(duration),
        UNIT_CD="s",
        SOURCESYSTEM_CD=SOURCE_TAG,
        IMPORT_DATE=now, UPDATE_DATE=now,
    ))


def _existing_patient_ids(db: Session) -> set[str]:
    rows = (
        db.query(PatientDimension.PATIENT_CD)
        .filter(PatientDimension.PATIENT_CD.like(f"{DEMO_PATIENT_PREFIX}%"))
        .all()
    )
    return {r[0] for r in rows}


def import_samples(
    db: Session,
    wav_files: list[Path],
    username: str,
    *,
    only_read_text: bool = True,
) -> Iterator[dict]:
    """
    Generator that imports each WAV as a DEMO patient + visit + trial observation
    + audio_uuid observation, yielding live progress events.

    Idempotent on PATIENT_CD. The final event is a summary dict with:
        {"phase": "import_done", "imported": N, "skipped": N,
         "trial_ids": [...], "by_group": {"Kontrolle": N, "Parkinson": N}}

    Args:
        only_read_text: if True (default), prefer ReadText files when both
            ReadText and SpontaneousDialogue exist for the same speaker.
    """
    samples: dict[str, SampleMeta] = {}
    for path in wav_files:
        meta = _parse_filename(path)
        if meta is None:
            continue
        # Prefer ReadText over SpontaneousDialogue when both exist
        cur = samples.get(meta.file_id)
        if cur is None:
            samples[meta.file_id] = meta
            continue
        # tiebreaker
        if only_read_text and "ReadText" in str(meta.abs_path) and "ReadText" not in str(cur.abs_path):
            samples[meta.file_id] = meta

    existing = _existing_patient_ids(db)

    pat_repo = PatientRepository(db)
    visit_repo = VisitRepository(db)
    obs_repo = ObservationRepository(db)
    # Demo data is shared across all users (USER_ID = 0 == public bucket).
    PUBLIC_USER_ID = 0
    trial_ids: list[int] = []
    by_group = {"Kontrolle": 0, "Parkinson": 0}
    imported = 0
    skipped = 0

    sorted_samples = sorted(samples.values(), key=lambda s: s.file_id)
    duration_cd = AUDIO_DURATION_CONCEPTS.get(DEMO_TASK)
    for i, meta in enumerate(sorted_samples):
        patient_cd = f"{DEMO_PATIENT_PREFIX}{meta.file_id}"
        if patient_cd in existing:
            # Self-heal: ensure existing demo patients are globally visible
            # (older imports pinned them to the importing user only).
            existing_patient = (
                db.query(PatientDimension)
                .filter(PatientDimension.PATIENT_CD == patient_cd)
                .first()
            )
            if existing_patient is not None:
                pat_repo.ensure_user_access(existing_patient.PATIENT_NUM, PUBLIC_USER_ID)
                # Self-heal: backfill audio_duration for older imports that
                # passed audio_duration=None.  Reads only the WAV header.
                if duration_cd is not None:
                    _backfill_demo_duration(db, existing_patient.PATIENT_NUM, meta, duration_cd)
            skipped += 1
            yield {
                "phase": "import", "current": i + 1, "total": len(sorted_samples),
                "kind": "skipped", "patient_cd": patient_cd,
            }
            continue

        gender = _synth_gender(meta.file_id)
        birth_date = _synth_birth_date(meta.file_id, meta.group)
        sex_cd = GENDER_TO_SNOMED.get(gender, gender)

        # Patient
        patient, _ = pat_repo.get_or_create(
            patient_cd=patient_cd,
            BIRTH_DATE=birth_date,
            SEX_CD=sex_cd,
            VITAL_STATUS_CD="SCTID: 438949009",
            SOURCESYSTEM_CD=SOURCE_TAG,
        )
        # Public access — demo data is shared across all users.
        pat_repo.ensure_user_access(patient.PATIENT_NUM, PUBLIC_USER_ID)

        # Visit (test_date = 2017-09-26 is the start of MDVR-KCL recording)
        session_id = f"DEMO_MDVR_{meta.file_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
        visit, _ = visit_repo.get_or_create(
            patient_num=patient.PATIENT_NUM,
            session_analysis_id=session_id,
            START_DATE="2017-09-26",
            INOUT_CD="O",
            SOURCESYSTEM_CD=SOURCE_TAG,
        )

        # Session-level: SESSION_ID + GROUP
        now = datetime.now().isoformat()
        db.add(ObservationFact(
            ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
            PATIENT_NUM=patient.PATIENT_NUM,
            CONCEPT_CD="SS:SESSION:SESSION_ID",
            CATEGORY_CHAR="session",
            VALTYPE_CD="T",
            TVAL_CHAR=session_id,
            START_DATE=now, INSTANCE_NUM=1,
            SOURCESYSTEM_CD=SOURCE_TAG, IMPORT_DATE=now, UPDATE_DATE=now,
        ))
        db.add(ObservationFact(
            ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
            PATIENT_NUM=patient.PATIENT_NUM,
            CONCEPT_CD="SS:SESSION:GROUP",
            CATEGORY_CHAR="session",
            VALTYPE_CD="T",
            TVAL_CHAR=meta.group,
            START_DATE=now, INSTANCE_NUM=1,
            SOURCESYSTEM_CD=SOURCE_TAG, IMPORT_DATE=now, UPDATE_DATE=now,
        ))

        # Audio: WAV -> MP3, measure real duration
        wav_bytes = meta.abs_path.read_bytes()
        try:
            duration_s = AudioSegment.from_file(meta.abs_path).duration_seconds
        except Exception:
            duration_s = None
        audio_uuid = convert_and_save_mp3(wav_bytes, source_format="wav")

        # Trial observations (CATEGORY="picture" placeholder, no GPT/NLP)
        observations = obs_repo.bulk_create_from_metrics(
            encounter_num=visit.ENCOUNTER_NUM,
            patient_num=patient.PATIENT_NUM,
            task_type=DEMO_TASK,
            metrics={},
            transcript=None,
            audio_uuid=audio_uuid,
            audio_duration=duration_s,
            attempt_id=meta.file_id,
            provider_id=meta.file_id,
            instance_num=1,
        )

        # Note (visible as analysis note)
        note_text = (
            f"{DEMO_NOTE}\n"
            f"File: {meta.raw_name}\n"
            f"Group: {meta.group}"
            + (f"\nH&Y: {meta.hy_stage}" if meta.hy_stage is not None else "")
            + (f"  UPDRS-II: {meta.updrs_ii}" if meta.updrs_ii is not None else "")
            + (f"  UPDRS-III: {meta.updrs_iii}" if meta.updrs_iii is not None else "")
        )
        db.add(NoteFact(
            PATIENT_NUM=patient.PATIENT_NUM,
            ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
            CATEGORY_CHAR="session",
            NAME_CHAR="Demo-Daten Quelle",
            NOTE_TEXT=note_text,
            SOURCESYSTEM_CD=SOURCE_TAG,
            IMPORT_DATE=now, UPDATE_DATE=now,
        ))

        db.flush()
        # Trial observation_id = first metric or audio_uuid row
        if observations:
            trial_ids.append(observations[0].OBSERVATION_ID)
        else:
            # bulk_create_from_metrics with empty metrics still creates audio rows
            audio_obs = (
                db.query(ObservationFact.OBSERVATION_ID)
                .filter(
                    ObservationFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM,
                    ObservationFact.CATEGORY_CHAR == DEMO_TASK,
                    ObservationFact.CONCEPT_CD == f"SS:{DEMO_TASK.upper()}:AUDIO_UUID",
                )
                .first()
            )
            if audio_obs:
                trial_ids.append(audio_obs[0])

        imported += 1
        by_group[meta.group] += 1
        yield {
            "phase": "import", "current": i + 1, "total": len(sorted_samples),
            "kind": "imported", "patient_cd": patient_cd,
        }

    db.commit()
    yield {
        "phase": "import_done",
        "imported": imported,
        "skipped": skipped,
        "trial_ids": trial_ids,
        "by_group": by_group,
        "total_samples_seen": len(sorted_samples),
    }


# ── Status / cleanup ────────────────────────────────────────

def get_status(db: Optional[Session] = None) -> dict:
    """Return cache + DB import state. db is optional: if omitted, n_imported is None."""
    n_imported = None
    if db is not None:
        n_imported = (
            db.query(PatientDimension)
            .filter(PatientDimension.PATIENT_CD.like(f"{DEMO_PATIENT_PREFIX}%"))
            .count()
        )
    return {
        "downloaded": is_downloaded(),
        "extracted": is_extracted(),
        "zip_path": str(_zip_path()),
        "extracted_dir": str(_extracted_dir()),
        "zip_size_mb": (
            round(_zip_path().stat().st_size / 1_048_576, 1)
            if _zip_path().exists() else None
        ),
        "n_imported": n_imported,
    }


def delete_imported_samples(db: Session) -> dict:
    """
    Delete all DEMO-MDVR-* patients (cascades to visits, observations, notes)
    and their associated MP3 files. Returns counts.
    """
    from db.repositories.observation_repository import AUDIO_UUID_CONCEPTS
    from service.audio_storage_service import delete_mp3

    audio_uuid_cds = list(AUDIO_UUID_CONCEPTS.values())

    # Find all demo patients
    patients = (
        db.query(PatientDimension)
        .filter(PatientDimension.PATIENT_CD.like(f"{DEMO_PATIENT_PREFIX}%"))
        .all()
    )
    if not patients:
        return {"patients_deleted": 0, "mp3_deleted": 0}

    # Collect audio UUIDs first so we can delete the MP3 files
    patient_nums = [p.PATIENT_NUM for p in patients]
    audio_obs = (
        db.query(ObservationFact.TVAL_CHAR)
        .filter(
            ObservationFact.PATIENT_NUM.in_(patient_nums),
            ObservationFact.CONCEPT_CD.in_(audio_uuid_cds),
        )
        .all()
    )
    mp3_deleted = 0
    for (uuid,) in audio_obs:
        if uuid and delete_mp3(uuid):
            mp3_deleted += 1

    # Cascade delete via ORM relationships (PatientDimension -> visits, observations, notes)
    for p in patients:
        db.delete(p)
    db.commit()

    return {"patients_deleted": len(patients), "mp3_deleted": mp3_deleted}


def cleanup_extracted():
    """Remove extracted files (kept zip cache)."""
    d = _extracted_dir()
    if d.exists():
        shutil.rmtree(d)
