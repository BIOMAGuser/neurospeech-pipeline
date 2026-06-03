"""
Data CRUD endpoints — reads from i2b2 star schema, API format unchanged.

All responses maintain backward compatibility with the legacy API contract
via the trial_serializer compatibility layer.
"""

import logging
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models_star import (
    PatientDimension, VisitDimension, ObservationFact, NoteFact, UserPatientLookup,
)
from db.repositories.patient_repository import PatientRepository
from db.repositories.visit_repository import VisitRepository
from db.repositories.observation_repository import ObservationRepository
from service.auth_service import get_current_user, User
from service.audio_storage_service import get_mp3_path, delete_mp3
from service.trial_serializer import (
    serialize_patient_for_list,
    serialize_visit_for_list,
    serialize_visit_detail,
    find_audio_uuid_for_trial,
    find_audio_uuid_by_observation_id,
)
from service.fhir_service import (
    patient_to_fhir_bundle, visit_to_fhir_bundle, all_to_fhir_bundle,
    fhir_bundle_to_patient_data, fhir_bundle_to_analysis_data,
)
from service.observation_builder import write_to_star_schema, username_to_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Access control helpers
# ---------------------------------------------------------------------------

def _check_patient_access(db: Session, patient_num: int, user: User):
    """Raise 403 if non-admin user doesn't have access to this patient."""
    if user.is_admin:
        return
    repo = PatientRepository(db)
    if not repo.check_access(patient_num, username_to_user_id(user.username), user.is_admin):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Patienten")


def _patient_access_filter(db, query, user: User):
    """Apply user-based patient filtering to a query involving PatientDimension."""
    if user.is_admin:
        return query
    return (query
            .join(UserPatientLookup,
                  UserPatientLookup.PATIENT_NUM == PatientDimension.PATIENT_NUM)
            .filter(or_(
                UserPatientLookup.USER_ID == username_to_user_id(user.username),
                UserPatientLookup.USER_ID == 0,
            )))


# ---------------------------------------------------------------------------
# Patient listing
# ---------------------------------------------------------------------------

@router.get("/patients")
def list_patients(
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List patients with their analysis (visit) count."""
    query = (
        db.query(
            PatientDimension,
            func.count(func.distinct(VisitDimension.ENCOUNTER_NUM)).label("visit_count"),
        )
        .outerjoin(VisitDimension,
                   VisitDimension.PATIENT_NUM == PatientDimension.PATIENT_NUM)
    )

    query = _patient_access_filter(db, query, current_user)

    rows = (query
            .group_by(PatientDimension.PATIENT_NUM)
            .order_by(PatientDimension.PATIENT_NUM.desc())
            .offset(offset).limit(limit)
            .all())

    result = []
    for patient, visit_count in rows:
        # Resolve created_by from USER_PATIENT_LOOKUP
        upl = (db.query(UserPatientLookup)
               .filter(UserPatientLookup.PATIENT_NUM == patient.PATIENT_NUM)
               .first())
        created_by = upl.NAME_CHAR if upl else None

        item = serialize_patient_for_list(patient, visit_count)
        item["created_by"] = created_by
        result.append(item)

    return result


# ---------------------------------------------------------------------------
# Trial audio
# ---------------------------------------------------------------------------

@router.get("/trials/{trial_id}/audio")
def get_trial_audio(
    trial_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve the MP3 audio file for a trial (observation_id)."""
    audio_uuid, patient_num = find_audio_uuid_by_observation_id(db, trial_id)

    if patient_num is not None:
        _check_patient_access(db, patient_num, current_user)

    if not audio_uuid:
        raise HTTPException(status_code=404, detail="Kein Audio vorhanden")

    path = get_mp3_path(audio_uuid)
    if not path:
        raise HTTPException(status_code=404, detail="Audiodatei nicht gefunden")

    return FileResponse(path, media_type="audio/mpeg", filename=f"trial_{trial_id}.mp3")


# ---------------------------------------------------------------------------
# Analysis (Visit) detail
# ---------------------------------------------------------------------------

@router.get("/analyses/{analysis_id}")
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single analysis (visit) with its trials (observations)."""
    visit = db.query(VisitDimension).filter(
        VisitDimension.ENCOUNTER_NUM == analysis_id
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    _check_patient_access(db, visit.PATIENT_NUM, current_user)

    patient = db.query(PatientDimension).filter(
        PatientDimension.PATIENT_NUM == visit.PATIENT_NUM
    ).first()

    observations = (db.query(ObservationFact)
                    .filter(ObservationFact.ENCOUNTER_NUM == analysis_id)
                    .all())

    notes = (db.query(NoteFact)
             .filter(NoteFact.ENCOUNTER_NUM == analysis_id)
             .all())

    return serialize_visit_detail(visit, observations, notes, patient)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/analyses/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a visit and its observations (including MP3 files)."""
    visit = db.query(VisitDimension).filter(
        VisitDimension.ENCOUNTER_NUM == analysis_id
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    _check_patient_access(db, visit.PATIENT_NUM, current_user)

    # Delete MP3 files for all audio UUID observations
    audio_obs = (db.query(ObservationFact)
                 .filter(
                     ObservationFact.ENCOUNTER_NUM == analysis_id,
                     ObservationFact.CONCEPT_CD.in_([
                         "SS:VEGGIE:AUDIO_UUID", "SS:SAYING:AUDIO_UUID",
                         "SS:PICTURE:AUDIO_UUID", "SS:VOICESAMPLE:AUDIO_UUID",
                     ]),
                 ).all())
    for obs in audio_obs:
        if obs.TVAL_CHAR:
            delete_mp3(obs.TVAL_CHAR)

    # Cascade: delete observations, notes, then visit
    db.query(ObservationFact).filter(ObservationFact.ENCOUNTER_NUM == analysis_id).delete()
    db.query(NoteFact).filter(NoteFact.ENCOUNTER_NUM == analysis_id).delete()
    db.delete(visit)
    db.commit()

    logger.info("Visit %d deleted by user: %s", analysis_id, current_user.username)
    return {"status": "ok"}


@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a patient and all their visits/observations (cascade), including MP3 files."""
    patient = db.query(PatientDimension).filter(
        PatientDimension.PATIENT_NUM == patient_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden")

    _check_patient_access(db, patient.PATIENT_NUM, current_user)

    # Collect all visits for this patient
    visits = db.query(VisitDimension).filter(
        VisitDimension.PATIENT_NUM == patient_id
    ).all()

    for visit in visits:
        # Delete MP3 files
        audio_obs = (db.query(ObservationFact)
                     .filter(
                         ObservationFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM,
                         ObservationFact.CONCEPT_CD.in_([
                             "SS:VEGGIE:AUDIO_UUID", "SS:SAYING:AUDIO_UUID",
                         "SS:PICTURE:AUDIO_UUID", "SS:VOICESAMPLE:AUDIO_UUID",
                         ]),
                     ).all())
        for obs in audio_obs:
            if obs.TVAL_CHAR:
                delete_mp3(obs.TVAL_CHAR)

    # Cascade deletes via ORM relationships
    db.delete(patient)
    db.commit()

    logger.info("Patient %d deleted by user: %s", patient_id, current_user.username)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Export (FHIR)
# ---------------------------------------------------------------------------

@router.get("/patients/{patient_id}/export")
def export_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export a single patient with all visits and observations as FHIR Bundle."""
    patient = db.query(PatientDimension).filter(
        PatientDimension.PATIENT_NUM == patient_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden")

    _check_patient_access(db, patient.PATIENT_NUM, current_user)

    logger.info("Patient export id=%d by user=%s", patient_id, current_user.username)
    bundle = patient_to_fhir_bundle(patient, db)
    db.commit()
    return bundle


@router.get("/analyses/{analysis_id}/export")
def export_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export a single analysis (visit) with its observations as FHIR Bundle."""
    visit = db.query(VisitDimension).filter(
        VisitDimension.ENCOUNTER_NUM == analysis_id
    ).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    _check_patient_access(db, visit.PATIENT_NUM, current_user)

    logger.info("Analysis export id=%d by user=%s", analysis_id, current_user.username)
    bundle = visit_to_fhir_bundle(visit, db)
    db.commit()
    return bundle


@router.get("/export")
def export_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Export all patients as FHIR Bundle."""
    query = db.query(PatientDimension)
    query = _patient_access_filter(db, query, current_user)
    patients = query.order_by(PatientDimension.PATIENT_NUM.desc()).all()

    logger.info("Data export by user=%s", current_user.username)
    bundle = all_to_fhir_bundle(patients, db)
    db.commit()
    return bundle


# ---------------------------------------------------------------------------
# Patient analyses listing
# ---------------------------------------------------------------------------

@router.get("/patients/{patient_id}/analyses")
def list_patient_analyses(
    patient_id: int,
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all visits (analyses) for a specific patient."""
    patient = db.query(PatientDimension).filter(
        PatientDimension.PATIENT_NUM == patient_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden")

    _check_patient_access(db, patient.PATIENT_NUM, current_user)

    visits = (db.query(VisitDimension)
              .filter(VisitDimension.PATIENT_NUM == patient_id)
              .order_by(VisitDimension.ENCOUNTER_NUM.desc())
              .offset(offset).limit(limit)
              .all())

    result = []
    for visit in visits:
        # Get session-level observations
        session_obs = (db.query(ObservationFact)
                       .filter(
                           ObservationFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM,
                           ObservationFact.CATEGORY_CHAR == "session",
                       ).all())

        # Count distinct task types
        trial_count = (db.query(func.count(func.distinct(ObservationFact.CATEGORY_CHAR)))
                       .filter(
                           ObservationFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM,
                           ObservationFact.CATEGORY_CHAR.in_(["veggie", "saying", "picture"]),
                       ).scalar()) or 0

        result.append(serialize_visit_for_list(visit, session_obs, trial_count))

    return result


# ---------------------------------------------------------------------------
# Import helpers & endpoints
# ---------------------------------------------------------------------------

def _parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.utcnow()


def _parse_birth_date(value) -> str | None:
    """Parse a date string safely, returning None on failure."""
    if not value or not isinstance(value, str):
        return None
    try:
        date.fromisoformat(value[:10])
        return value[:10]
    except (ValueError, IndexError):
        return None


def _import_analysis_star(analysis_data: dict, patient: PatientDimension,
                          username: str, db: Session) -> str:
    """Import a single analysis into star schema. Returns 'created' or 'skipped'."""
    session_id = analysis_data.get("session_analysis_id")
    if not session_id:
        raise HTTPException(status_code=422, detail="Analysis missing session_analysis_id")

    # Dedup check via session ID observation
    visit_repo = VisitRepository(db)
    existing = visit_repo.find_by_session_id(session_id)
    if existing:
        return "skipped"

    analysis_date = analysis_data.get("date")
    if analysis_date and isinstance(analysis_date, str):
        try:
            date.fromisoformat(analysis_date)
        except ValueError:
            analysis_date = date.today().isoformat()
    else:
        analysis_date = date.today().isoformat()

    trials_data = analysis_data.get("trials", [])

    for td in trials_data:
        task_type = td.get("task", "")
        metrics = td.get("metrics", {})
        # Also pick up top-level fields as metrics
        if td.get("points") is not None and "points" not in metrics:
            metrics["points"] = td["points"]
        if td.get("total_word_count") is not None and "total_word_count" not in metrics:
            metrics["total_word_count"] = td["total_word_count"]

        write_to_star_schema(
            db,
            patient_id=patient.PATIENT_CD,
            session_analysis_id=session_id,
            test_date=analysis_date,
            moca_score=analysis_data.get("moca_score"),
            group=analysis_data.get("group"),
            notes=analysis_data.get("notes"),
            task_type=task_type,
            metrics=metrics,
            transcript=td.get("transcript"),
            audio_uuid=None,  # Audio not included in JSON import
            audio_duration=td.get("audio_duration_seconds"),
            attempt_id=td.get("attempt_id"),
            username=username,
        )

    db.flush()
    return "created"


@router.post("/import/patient")
def import_patient(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import a patient with analyses from FHIR Bundle JSON."""
    if payload.get("resourceType") == "Bundle":
        payload = fhir_bundle_to_patient_data(payload)

    patient_data = payload.get("patient")
    if not patient_data or not patient_data.get("patient_id"):
        raise HTTPException(status_code=422, detail="Missing patient.patient_id")

    analyses_data = patient_data.get("analyses")
    if not isinstance(analyses_data, list):
        raise HTTPException(status_code=422, detail="Missing patient.analyses")

    for i, a in enumerate(analyses_data):
        if not a.get("session_analysis_id"):
            raise HTTPException(
                status_code=422,
                detail=f"Analysis at index {i} missing session_analysis_id",
            )

    try:
        patient_repo = PatientRepository(db)
        patient, patient_created = patient_repo.get_or_create(
            patient_cd=patient_data["patient_id"],
            SEX_CD=patient_data.get("gender"),
            BIRTH_DATE=_parse_birth_date(patient_data.get("birth_date")),
        )
        patient_repo.ensure_user_access(patient.PATIENT_NUM, username_to_user_id(current_user.username))

        analyses_created = 0
        analyses_skipped = 0
        trials_created = 0

        for a_data in analyses_data:
            result = _import_analysis_star(a_data, patient, current_user.username, db)
            if result == "created":
                analyses_created += 1
                trials_created += len(a_data.get("trials", []))
            else:
                analyses_skipped += 1

        db.commit()
        logger.info(
            "Patient import by user=%s: patient=%s created=%s analyses_created=%d",
            current_user.username, patient_data["patient_id"], patient_created, analyses_created,
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate session_analysis_id")
    except Exception as e:
        db.rollback()
        logger.error("Import failed: %s", e)
        raise HTTPException(status_code=500, detail="Import failed")

    return {
        "patients_created": 1 if patient_created else 0,
        "analyses_created": analyses_created,
        "analyses_skipped": analyses_skipped,
        "trials_created": trials_created,
    }


@router.post("/import/analysis")
def import_analysis_endpoint(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import a single analysis from FHIR Bundle JSON."""
    if payload.get("resourceType") == "Bundle":
        payload = fhir_bundle_to_analysis_data(payload)

    analysis_data = payload.get("analysis")
    if not analysis_data:
        raise HTTPException(status_code=422, detail="Missing analysis")

    patient_id_str = payload.get("patient_id")
    if not patient_id_str:
        raise HTTPException(status_code=422, detail="Missing patient_id")

    if not analysis_data.get("session_analysis_id"):
        raise HTTPException(status_code=422, detail="Analysis missing session_analysis_id")

    try:
        patient_repo = PatientRepository(db)
        patient, patient_created = patient_repo.get_or_create(
            patient_cd=patient_id_str,
        )
        patient_repo.ensure_user_access(patient.PATIENT_NUM, username_to_user_id(current_user.username))

        result = _import_analysis_star(analysis_data, patient, current_user.username, db)
        trials_created = len(analysis_data.get("trials", [])) if result == "created" else 0

        db.commit()
        logger.info(
            "Analysis import by user=%s: patient=%s session=%s result=%s",
            current_user.username, patient_id_str,
            analysis_data.get("session_analysis_id"), result,
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate session_analysis_id")
    except Exception as e:
        db.rollback()
        logger.error("Analysis import failed: %s", e)
        raise HTTPException(status_code=500, detail="Import failed")

    return {
        "patients_created": 1 if patient_created else 0,
        "analyses_created": 1 if result == "created" else 0,
        "analyses_skipped": 1 if result == "skipped" else 0,
        "trials_created": trials_created,
    }
