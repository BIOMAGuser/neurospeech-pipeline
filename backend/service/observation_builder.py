"""
Service to write measurement data into the i2b2 star schema.

Orchestrates creation of PatientDimension, VisitDimension, ObservationFact
entries from the same input data that the legacy schema receives.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.models_star import (
    PatientDimension, VisitDimension, ObservationFact, NoteFact, UserPatientLookup,
)
from db.repositories.patient_repository import PatientRepository
from db.repositories.visit_repository import VisitRepository
from db.repositories.observation_repository import ObservationRepository
from db.seeds.concepts import GENDER_TO_SNOMED


def username_to_user_id(username: str) -> int:
    """Derive a stable numeric user ID from a username string.

    The User model has no numeric ID, so we hash the username to get
    a consistent integer for USER_PATIENT_LOOKUP.USER_ID.
    Uses hashlib for deterministic hashing across process restarts.
    """
    import hashlib
    return int(hashlib.sha256(username.encode()).hexdigest()[:8], 16)

logger = logging.getLogger(__name__)


def write_to_star_schema(
    db: Session,
    *,
    # Patient data
    patient_id: str,
    birth_date: str | None = None,
    gender: str | None = None,
    # Visit/Analysis data
    session_analysis_id: str | None = None,
    test_date: str | None = None,
    moca_score: int | None = None,
    group: str | None = None,
    notes: str | None = None,
    # Trial/Measurement data
    task_type: str,
    metrics: dict[str, Any],
    transcript: str | None = None,
    audio_uuid: str | None = None,
    audio_duration: float | None = None,
    attempt_id: str | None = None,
    # Context
    username: str | None = None,
) -> dict:
    """
    Write a complete measurement to the star schema.

    Creates/reuses PatientDimension, VisitDimension, and creates
    ObservationFact rows for all metrics. Also creates session-level
    observations (MoCA, group) and notes.

    Returns dict with created IDs: {patient_num, encounter_num, observation_count}
    """
    patient_repo = PatientRepository(db)
    visit_repo = VisitRepository(db)
    obs_repo = ObservationRepository(db)

    now = datetime.now().isoformat()

    # ── 1. Patient ────────────────────────────────────────────
    sex_cd = GENDER_TO_SNOMED.get(gender.lower(), gender) if gender else None

    patient, patient_created = patient_repo.get_or_create(
        patient_cd=patient_id,
        BIRTH_DATE=birth_date,
        SEX_CD=sex_cd,
        VITAL_STATUS_CD="SCTID: 438949009",  # alive
        SOURCESYSTEM_CD="SYSTEM",
    )

    # Ensure user access
    if username is not None:
        patient_repo.ensure_user_access(patient.PATIENT_NUM, username_to_user_id(username))

    # ── 2. Visit (= Analysis session) ────────────────────────
    visit, visit_created = visit_repo.get_or_create(
        patient_num=patient.PATIENT_NUM,
        session_analysis_id=session_analysis_id,
        START_DATE=test_date or now,
        INOUT_CD="O",  # outpatient
        SOURCESYSTEM_CD="SYSTEM",
    )

    # If this is a new visit, store session-level observations
    if visit_created:
        # Session analysis ID as observation
        if session_analysis_id:
            obs = ObservationFact(
                ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
                PATIENT_NUM=patient.PATIENT_NUM,
                CONCEPT_CD="SS:SESSION:SESSION_ID",
                CATEGORY_CHAR="session",
                VALTYPE_CD="T",
                TVAL_CHAR=session_analysis_id,
                START_DATE=now,
                INSTANCE_NUM=1,
                SOURCESYSTEM_CD="SYSTEM",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
            )
            db.add(obs)

        # MoCA score
        if moca_score is not None:
            obs = ObservationFact(
                ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
                PATIENT_NUM=patient.PATIENT_NUM,
                CONCEPT_CD="SS:SESSION:MOCA_SCORE",
                CATEGORY_CHAR="session",
                VALTYPE_CD="N",
                NVAL_NUM=moca_score,
                UNIT_CD="count",
                START_DATE=now,
                INSTANCE_NUM=1,
                SOURCESYSTEM_CD="SYSTEM",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
            )
            db.add(obs)

        # Patient group
        if group:
            obs = ObservationFact(
                ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
                PATIENT_NUM=patient.PATIENT_NUM,
                CONCEPT_CD="SS:SESSION:GROUP",
                CATEGORY_CHAR="session",
                VALTYPE_CD="T",
                TVAL_CHAR=group,
                START_DATE=now,
                INSTANCE_NUM=1,
                SOURCESYSTEM_CD="SYSTEM",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
            )
            db.add(obs)

        # Notes → NOTE_FACT
        if notes:
            note = NoteFact(
                PATIENT_NUM=patient.PATIENT_NUM,
                ENCOUNTER_NUM=visit.ENCOUNTER_NUM,
                CATEGORY_CHAR="session",
                NAME_CHAR="Analyse-Notizen",
                NOTE_TEXT=notes,
                SOURCESYSTEM_CD="SYSTEM",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
            )
            db.add(note)

    # ── 3. Task observations (metrics) ────────────────────────
    observations = obs_repo.bulk_create_from_metrics(
        encounter_num=visit.ENCOUNTER_NUM,
        patient_num=patient.PATIENT_NUM,
        task_type=task_type,
        metrics=metrics,
        transcript=transcript,
        audio_uuid=audio_uuid,
        audio_duration=audio_duration,
        attempt_id=attempt_id,
        provider_id=username,
        instance_num=1,
    )

    db.flush()

    return {
        "patient_num": patient.PATIENT_NUM,
        "encounter_num": visit.ENCOUNTER_NUM,
        "observation_count": len(observations),
        "patient_created": patient_created,
        "visit_created": visit_created,
    }
