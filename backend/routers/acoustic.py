"""
Acoustic feature endpoints — on-demand extraction from stored MP3 audio.

POST /trials/{observation_id}/acoustic
    Compute jitter / shimmer / MFCC / HNR / F0 from the trial's audio,
    persist to OBSERVATION_FACT (CATEGORY_CHAR='acoustic'). Idempotent —
    existing acoustic rows for the same trial anchor are deleted first.

GET /trials/{observation_id}/acoustic
    Return previously computed features for a trial, pivoted to flat JSON.
    404 if none exist yet.
"""

import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models_star import ObservationFact
from db.repositories.observation_repository import (
    AUDIO_DURATION_CONCEPTS,
    AUDIO_UUID_CONCEPTS,
    METRIC_CONCEPT_MAP,
)
from db.repositories.patient_repository import PatientRepository
from service.audio_storage_service import get_mp3_path
from service.auth_service import get_current_user, User
from service.observation_builder import username_to_user_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["acoustic"])

ACOUSTIC_CATEGORY = "acoustic"
TRIAL_CATEGORIES = ("veggie", "saying", "picture", "voicesample")


def _check_patient_access(db: Session, patient_num: int, user: User):
    if user.is_admin:
        return
    repo = PatientRepository(db)
    if not repo.check_access(patient_num, username_to_user_id(user.username), user.is_admin):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Patienten")


def _resolve_trial_anchor(db: Session, observation_id: int) -> ObservationFact:
    """Look up the trial anchor row. Must belong to a veggie/saying/picture trial."""
    obs = db.query(ObservationFact).filter(
        ObservationFact.OBSERVATION_ID == observation_id
    ).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Trial nicht gefunden")
    if obs.CATEGORY_CHAR not in TRIAL_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Observation gehört nicht zu einem Trial (category={obs.CATEGORY_CHAR})",
        )
    return obs


def _find_audio_uuid(db: Session, trial_anchor: ObservationFact) -> str | None:
    """Look up the audio_uuid observation for the given trial anchor."""
    uuid_cd = AUDIO_UUID_CONCEPTS.get(trial_anchor.CATEGORY_CHAR)
    if not uuid_cd:
        return None
    obs = (db.query(ObservationFact)
           .filter(
               ObservationFact.ENCOUNTER_NUM == trial_anchor.ENCOUNTER_NUM,
               ObservationFact.INSTANCE_NUM == trial_anchor.INSTANCE_NUM,
               ObservationFact.CONCEPT_CD == uuid_cd,
           )
           .first())
    return obs.TVAL_CHAR if obs else None


def _read_acoustic_features(db: Session, trial_anchor: ObservationFact) -> dict:
    """Pivot acoustic OBSERVATION_FACT rows back to a flat dict."""
    rows = (db.query(ObservationFact)
            .filter(
                ObservationFact.ENCOUNTER_NUM == trial_anchor.ENCOUNTER_NUM,
                ObservationFact.INSTANCE_NUM == trial_anchor.INSTANCE_NUM,
                ObservationFact.CATEGORY_CHAR == ACOUSTIC_CATEGORY,
            )
            .all())
    if not rows:
        return {}

    reverse_map = {v: k for k, v in METRIC_CONCEPT_MAP[ACOUSTIC_CATEGORY].items()}
    out: dict = {}
    for r in rows:
        key = reverse_map.get(r.CONCEPT_CD)
        if key is None:
            continue
        if r.NVAL_NUM is not None:
            out[key] = float(r.NVAL_NUM)
    return out


def _delete_existing_acoustic(db: Session, trial_anchor: ObservationFact) -> int:
    """Remove acoustic rows for this trial anchor. Returns count deleted."""
    deleted = (db.query(ObservationFact)
               .filter(
                   ObservationFact.ENCOUNTER_NUM == trial_anchor.ENCOUNTER_NUM,
                   ObservationFact.INSTANCE_NUM == trial_anchor.INSTANCE_NUM,
                   ObservationFact.CATEGORY_CHAR == ACOUSTIC_CATEGORY,
               )
               .delete(synchronize_session=False))
    return deleted


def _persist_features(db: Session, trial_anchor: ObservationFact, features: dict) -> int:
    """Insert one OBSERVATION_FACT row per non-null feature. Returns count inserted."""
    now = datetime.now().isoformat()
    concept_map = METRIC_CONCEPT_MAP[ACOUSTIC_CATEGORY]
    inserted = 0
    for metric_key, value in features.items():
        if value is None or metric_key.startswith("_"):
            continue
        concept_cd = concept_map.get(metric_key)
        if concept_cd is None:
            continue
        db.add(ObservationFact(
            ENCOUNTER_NUM=trial_anchor.ENCOUNTER_NUM,
            PATIENT_NUM=trial_anchor.PATIENT_NUM,
            CONCEPT_CD=concept_cd,
            CATEGORY_CHAR=ACOUSTIC_CATEGORY,
            PROVIDER_ID=trial_anchor.PROVIDER_ID,
            START_DATE=now,
            INSTANCE_NUM=trial_anchor.INSTANCE_NUM,
            VALTYPE_CD="N",
            NVAL_NUM=float(value),
            SOURCESYSTEM_CD="ACOUSTIC",
            IMPORT_DATE=now,
            UPDATE_DATE=now,
        ))
        inserted += 1
    db.flush()
    return inserted


def _upsert_audio_duration(db: Session, trial_anchor: ObservationFact, duration_s: float | None) -> None:
    """
    Replace the trial's audio_duration observation with the measured value.
    Many existing trials have a wrong/placeholder duration from the analyze
    form-param; the acoustic pipeline is the authoritative source.
    """
    if duration_s is None or duration_s <= 0:
        return
    duration_cd = AUDIO_DURATION_CONCEPTS.get(trial_anchor.CATEGORY_CHAR)
    if duration_cd is None:
        return
    now = datetime.now().isoformat()
    db.query(ObservationFact).filter(
        ObservationFact.ENCOUNTER_NUM == trial_anchor.ENCOUNTER_NUM,
        ObservationFact.INSTANCE_NUM == trial_anchor.INSTANCE_NUM,
        ObservationFact.CONCEPT_CD == duration_cd,
    ).delete(synchronize_session=False)
    db.add(ObservationFact(
        ENCOUNTER_NUM=trial_anchor.ENCOUNTER_NUM,
        PATIENT_NUM=trial_anchor.PATIENT_NUM,
        CONCEPT_CD=duration_cd,
        CATEGORY_CHAR=trial_anchor.CATEGORY_CHAR,
        PROVIDER_ID=trial_anchor.PROVIDER_ID,
        START_DATE=now,
        INSTANCE_NUM=trial_anchor.INSTANCE_NUM,
        VALTYPE_CD="N",
        NVAL_NUM=float(duration_s),
        UNIT_CD="s",
        SOURCESYSTEM_CD="ACOUSTIC",
        IMPORT_DATE=now,
        UPDATE_DATE=now,
    ))
    db.flush()


@router.post("/trials/{observation_id}/acoustic")
def compute_trial_acoustic(
    observation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute acoustic features for a trial's audio and persist them."""
    trial_anchor = _resolve_trial_anchor(db, observation_id)
    _check_patient_access(db, trial_anchor.PATIENT_NUM, current_user)

    audio_uuid = _find_audio_uuid(db, trial_anchor)
    if not audio_uuid:
        raise HTTPException(status_code=404, detail="Kein Audio für diesen Trial vorhanden")

    mp3_path = get_mp3_path(audio_uuid)
    if not mp3_path:
        raise HTTPException(status_code=404, detail="Audiodatei nicht gefunden")

    # Defer the heavy import so the router is cheap to load and other tests
    # don't pay the parselmouth import cost.
    from analysis.acoustic import compute_acoustic_features

    t0 = time.perf_counter()
    try:
        features = compute_acoustic_features(mp3_path)
    except Exception as e:
        logger.exception("Acoustic extraction failed for trial %d", observation_id)
        raise HTTPException(status_code=500, detail=f"Akustik-Extraktion fehlgeschlagen: {e}")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    deleted = _delete_existing_acoustic(db, trial_anchor)
    inserted = _persist_features(db, trial_anchor, features)

    # The acoustic pipeline measures duration directly from the resampled audio
    # — overwrite any stale value (analyze form-param, demo loader fallback).
    duration_s = features.pop("_audio_duration_s", None)
    _upsert_audio_duration(db, trial_anchor, duration_s)
    db.commit()
    logger.info(
        "Acoustic features computed: trial=%d task=%s deleted=%d inserted=%d ms=%d",
        observation_id, trial_anchor.CATEGORY_CHAR, deleted, inserted, elapsed_ms,
    )

    return {
        "observation_id": observation_id,
        "task": trial_anchor.CATEGORY_CHAR,
        "audio_uuid": audio_uuid,
        "audio_duration_s": duration_s,
        "computation_ms": elapsed_ms,
        "feature_count": inserted,
        "features": features,
    }


@router.get("/trials/{observation_id}/acoustic")
def get_trial_acoustic(
    observation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return previously computed acoustic features for a trial."""
    trial_anchor = _resolve_trial_anchor(db, observation_id)
    _check_patient_access(db, trial_anchor.PATIENT_NUM, current_user)

    features = _read_acoustic_features(db, trial_anchor)
    if not features:
        raise HTTPException(
            status_code=404,
            detail="Noch keine akustischen Features berechnet — POST anstoßen",
        )

    return {
        "observation_id": observation_id,
        "task": trial_anchor.CATEGORY_CHAR,
        "feature_count": len(features),
        "features": features,
    }


# ── AcousticLab listing & scoring (Phase 2) ─────────────────

@router.get("/acoustic/trials")
def list_acoustic_trials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List every audio-bearing trial with patient demo + acoustic-computed flag."""
    from service.cohort_stats import list_trials_with_audio
    return list_trials_with_audio(db, current_user)


@router.get("/trials/{observation_id}/acoustic/score")
def get_trial_acoustic_score(
    observation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute the cohort-relative PD_Voice_Age_Score for a trial."""
    from service.cohort_stats import score_trial

    trial_anchor = _resolve_trial_anchor(db, observation_id)
    _check_patient_access(db, trial_anchor.PATIENT_NUM, current_user)

    result = score_trial(db, observation_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Noch keine akustischen Features für diesen Trial — POST /trials/{id}/acoustic zuerst",
        )
    return result


@router.get("/acoustic/cohort")
def get_acoustic_cohort(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compact summary of the current reference cohort (per-cell n + sample features)."""
    from service.cohort_stats import compute_cohort_posteriors, cohort_summary
    index = compute_cohort_posteriors(db)
    return cohort_summary(index)


# ── Demo-data loader (MDVR-KCL from Zenodo) ─────────────────

@router.get("/acoustic/samples/status")
def acoustic_samples_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cache state of the MDVR-KCL demo dataset + count of imported DB patients."""
    from service import sample_loader
    return sample_loader.get_status(db)


@router.delete("/acoustic/samples")
def delete_acoustic_samples(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk-delete all DEMO-MDVR-* patients and their cascaded data + MP3 files."""
    from service import sample_loader
    result = sample_loader.delete_imported_samples(db)
    logger.info(
        "Demo samples deleted by user=%s: patients=%d mp3=%d",
        current_user.username, result["patients_deleted"], result["mp3_deleted"],
    )
    return result


@router.post("/acoustic/samples/load")
def acoustic_samples_load(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream-load MDVR-KCL demo dataset from Zenodo into the DB.

    Returns ndjson — one JSON object per line:
        {"phase": "download", "status": "starting"|"progress"|"done"|"cached", ...}
        {"phase": "extract", "status": "starting"|"done", "wav_count": N}
        {"phase": "import", "current": i, "total": N, "patient_cd": "..."}
        {"phase": "done", "imported": N, "skipped": N, "trial_ids": [...]}
    """
    import json as _json

    from fastapi.responses import StreamingResponse
    from service import sample_loader

    def gen():
        try:
            # 1. Download (skips when cached)
            for evt in sample_loader.stream_download():
                yield _json.dumps(evt) + "\n"

            # 2. Extract
            yield _json.dumps({"phase": "extract", "status": "starting"}) + "\n"
            wavs = sample_loader.extract_zip()
            yield _json.dumps({
                "phase": "extract", "status": "done", "wav_count": len(wavs)
            }) + "\n"

            # 3. Import — generator yields per-sample progress live
            yield _json.dumps({
                "phase": "import", "status": "starting", "wav_count": len(wavs)
            }) + "\n"

            summary: dict | None = None
            for evt in sample_loader.import_samples(db, wavs, current_user.username):
                if evt.get("phase") == "import_done":
                    summary = evt
                else:
                    yield _json.dumps(evt) + "\n"

            # 4. Final summary
            if summary is None:
                summary = {"imported": 0, "skipped": 0, "trial_ids": [], "by_group": {}}
            yield _json.dumps({
                "phase": "done",
                "imported": summary["imported"],
                "skipped": summary["skipped"],
                "by_group": summary["by_group"],
                "trial_ids": summary["trial_ids"],
            }) + "\n"
        except Exception as e:
            logger.exception("Sample loader failed")
            yield _json.dumps({
                "phase": "error", "message": str(e), "type": type(e).__name__,
            }) + "\n"

    # Disable proxy buffering so each yielded line reaches the client immediately.
    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
