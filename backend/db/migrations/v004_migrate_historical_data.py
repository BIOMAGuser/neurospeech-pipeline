"""
v004: Migrate historical data from legacy schema to star schema.

Reads all existing Patient/Analysis/Trial rows and creates corresponding
PatientDimension/VisitDimension/ObservationFact rows. Idempotent.
"""

import json
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from db.database import SessionLocal
from db.models_star import (
    PatientDimension, VisitDimension, ObservationFact, NoteFact, UserPatientLookup,
)
from db.repositories.observation_repository import METRIC_CONCEPT_MAP
from db.seeds.concepts import GENDER_TO_SNOMED

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

# Legacy columns that map to metric keys per task
LEGACY_METRIC_COLUMNS = {
    "veggie": ["points", "correct_words", "unrelated_words", "duplicate_count",
               "filler_word_count", "total_word_count"],
    "saying": ["points", "filler_word_count", "total_word_count"],
    "picture": ["points", "sentence_count", "verb_count", "noun_count",
                "pronoun_count", "adverb_count", "adjective_count",
                "verb_ratio", "noun_ratio", "pronoun_ratio",
                "adverb_ratio", "adjective_ratio", "ttr",
                "avg_sentence_length", "filler_word_count", "total_word_count"],
}


def _extract_metrics(trial_row: dict, task_type: str) -> dict:
    """Extract metrics dict from a trial row, preferring metrics_json."""
    # Prefer metrics_json if available
    mj = trial_row.get("metrics_json")
    if mj:
        if isinstance(mj, str):
            try:
                return json.loads(mj)
            except (json.JSONDecodeError, ValueError):
                pass
        elif isinstance(mj, dict):
            return mj

    # Fall back to legacy columns
    metrics = {}
    for col in LEGACY_METRIC_COLUMNS.get(task_type, []):
        val = trial_row.get(col)
        if val is not None:
            # correct_words may be stored as JSON string
            if col == "correct_words" and isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    pass
            metrics[col] = val
    return metrics


def up(engine: Engine):
    """Migrate all historical data to star schema."""
    session = SessionLocal()
    try:
        # Check if migration already ran (idempotency)
        existing_patients = session.query(PatientDimension).count()
        if existing_patients > 0:
            logger.info("Star schema already has %d patients, skipping historical migration", existing_patients)
            return

        # Check if legacy tables exist (fresh install has no legacy tables)
        with engine.connect() as conn:
            tables = [row[0] for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()]
            if "patients" not in tables:
                logger.info("No legacy tables found (fresh install), skipping migration")
                return

            patient_count = conn.execute(text("SELECT COUNT(*) FROM patients")).scalar() or 0
            analysis_count = conn.execute(text("SELECT COUNT(*) FROM analyses")).scalar() or 0
            trial_count = conn.execute(text("SELECT COUNT(*) FROM trials")).scalar() or 0

        if patient_count == 0:
            logger.info("No legacy data to migrate")
            return

        logger.info("Migrating %d patients, %d analyses, %d trials", patient_count, analysis_count, trial_count)

        now = datetime.now().isoformat()
        patient_num_map = {}   # old patient.id → new PATIENT_NUM
        encounter_num_map = {}  # old analysis.id → new ENCOUNTER_NUM
        user_id_map = {}  # username → user_id (from users.db)

        # ── Migrate Patients ─────────────────────────────────
        with engine.connect() as conn:
            patients = conn.execute(text(
                "SELECT id, patient_id, birth_date, gender, created_by, created_at FROM patients"
            )).fetchall()

        for row in patients:
            old_id, patient_cd, birth_date, gender, created_by, created_at = row

            sex_cd = GENDER_TO_SNOMED.get(gender.lower(), gender) if gender else None

            pd = PatientDimension(
                PATIENT_CD=patient_cd,
                BIRTH_DATE=str(birth_date) if birth_date else None,
                SEX_CD=sex_cd,
                VITAL_STATUS_CD="SCTID: 438949009",
                SOURCESYSTEM_CD="LEGACY_MIGRATION",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
                CREATED_AT=str(created_at) if created_at else now,
            )
            session.add(pd)
            session.flush()
            patient_num_map[old_id] = pd.PATIENT_NUM

            # Create user-patient access (lookup user_id later)
            if created_by:
                if created_by not in user_id_map:
                    user_id_map[created_by] = created_by  # store username, resolve later

        logger.info("Migrated %d patients", len(patient_num_map))

        # ── Migrate Analyses → Visits ────────────────────────
        with engine.connect() as conn:
            analyses = conn.execute(text(
                "SELECT id, patient_id, date, moca_score, \"group\", notes, "
                "session_analysis_id, exported_at, created_at FROM analyses"
            )).fetchall()

        for row in analyses:
            (old_id, old_patient_id, date_, moca_score, group_, notes,
             session_analysis_id, exported_at, created_at) = row

            patient_num = patient_num_map.get(old_patient_id)
            if patient_num is None:
                logger.warning("Skipping analysis %d: patient %d not found in map", old_id, old_patient_id)
                continue

            vd = VisitDimension(
                PATIENT_NUM=patient_num,
                ACTIVE_STATUS_CD="SCTID: 55561003",
                START_DATE=str(date_) if date_ else now,
                INOUT_CD="O",
                SOURCESYSTEM_CD="LEGACY_MIGRATION",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
                CREATED_AT=str(created_at) if created_at else now,
            )
            session.add(vd)
            session.flush()
            encounter_num_map[old_id] = vd.ENCOUNTER_NUM

            # Session-level observations
            if session_analysis_id:
                session.add(ObservationFact(
                    ENCOUNTER_NUM=vd.ENCOUNTER_NUM,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD="SS:SESSION:SESSION_ID",
                    CATEGORY_CHAR="session",
                    VALTYPE_CD="T",
                    TVAL_CHAR=session_analysis_id,
                    START_DATE=now,
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))

            if moca_score is not None:
                session.add(ObservationFact(
                    ENCOUNTER_NUM=vd.ENCOUNTER_NUM,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD="SS:SESSION:MOCA_SCORE",
                    CATEGORY_CHAR="session",
                    VALTYPE_CD="N",
                    NVAL_NUM=moca_score,
                    UNIT_CD="count",
                    START_DATE=now,
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))

            if group_:
                session.add(ObservationFact(
                    ENCOUNTER_NUM=vd.ENCOUNTER_NUM,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD="SS:SESSION:GROUP",
                    CATEGORY_CHAR="session",
                    VALTYPE_CD="T",
                    TVAL_CHAR=group_,
                    START_DATE=now,
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))

            if notes:
                session.add(NoteFact(
                    PATIENT_NUM=patient_num,
                    ENCOUNTER_NUM=vd.ENCOUNTER_NUM,
                    CATEGORY_CHAR="session",
                    NAME_CHAR="Analyse-Notizen",
                    NOTE_TEXT=notes,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))

        logger.info("Migrated %d analyses → visits", len(encounter_num_map))

        # ── Migrate Trials → Observations ────────────────────
        observation_count = 0

        with engine.connect() as conn:
            # Fetch all columns including legacy metrics
            trial_rows = conn.execute(text(
                "SELECT id, analysis_id, task, processed_at, attempt_id, "
                "transcript, audio_duration_seconds, audio_uuid, total_word_count, "
                "metrics_json, points, correct_words, unrelated_words, duplicate_count, "
                "filler_word_count, sentence_count, verb_count, noun_count, "
                "pronoun_count, adverb_count, adjective_count, "
                "verb_ratio, noun_ratio, pronoun_ratio, adverb_ratio, adjective_ratio, "
                "ttr, avg_sentence_length "
                "FROM trials"
            )).fetchall()

        # Column names for dict conversion
        trial_columns = [
            "id", "analysis_id", "task", "processed_at", "attempt_id",
            "transcript", "audio_duration_seconds", "audio_uuid", "total_word_count",
            "metrics_json", "points", "correct_words", "unrelated_words", "duplicate_count",
            "filler_word_count", "sentence_count", "verb_count", "noun_count",
            "pronoun_count", "adverb_count", "adjective_count",
            "verb_ratio", "noun_ratio", "pronoun_ratio", "adverb_ratio", "adjective_ratio",
            "ttr", "avg_sentence_length",
        ]

        for i, row in enumerate(trial_rows):
            trial_dict = dict(zip(trial_columns, row))
            old_analysis_id = trial_dict["analysis_id"]
            task_type = trial_dict["task"]

            encounter_num = encounter_num_map.get(old_analysis_id)
            if encounter_num is None:
                logger.warning("Skipping trial %d: analysis %d not found", trial_dict["id"], old_analysis_id)
                continue

            # Get patient_num from visit
            visit = session.query(VisitDimension).filter(
                VisitDimension.ENCOUNTER_NUM == encounter_num
            ).first()
            if not visit:
                continue
            patient_num = visit.PATIENT_NUM

            # Extract metrics
            metrics = _extract_metrics(trial_dict, task_type)

            # Build observation rows using the concept map
            concept_map = METRIC_CONCEPT_MAP.get(task_type, {})

            for metric_key, value in metrics.items():
                if value is None:
                    continue
                concept_cd = concept_map.get(metric_key)
                if not concept_cd:
                    continue

                if isinstance(value, (list, dict)):
                    valtype = "T"
                    tval = json.dumps(value, ensure_ascii=False)
                    nval = None
                elif isinstance(value, (int, float)):
                    valtype = "N"
                    nval = value
                    tval = None
                elif isinstance(value, str):
                    valtype = "T"
                    tval = value
                    nval = None
                else:
                    continue

                session.add(ObservationFact(
                    ENCOUNTER_NUM=encounter_num,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD=concept_cd,
                    CATEGORY_CHAR=task_type,
                    VALTYPE_CD=valtype,
                    NVAL_NUM=nval,
                    TVAL_CHAR=tval,
                    START_DATE=str(trial_dict.get("processed_at") or now),
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))
                observation_count += 1

            # Transcript
            transcript_concepts = {
                "veggie": "SS:VEGGIE:TRANSCRIPT",
                "saying": "SS:SAYING:TRANSCRIPT",
                "picture": "SS:PICTURE:TRANSCRIPT",
            }
            transcript = trial_dict.get("transcript")
            if transcript and task_type in transcript_concepts:
                session.add(ObservationFact(
                    ENCOUNTER_NUM=encounter_num,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD=transcript_concepts[task_type],
                    CATEGORY_CHAR=task_type,
                    VALTYPE_CD="T",
                    TVAL_CHAR=transcript,
                    START_DATE=str(trial_dict.get("processed_at") or now),
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))
                observation_count += 1

            # Audio UUID
            audio_uuid_concepts = {
                "veggie": "SS:VEGGIE:AUDIO_UUID",
                "saying": "SS:SAYING:AUDIO_UUID",
                "picture": "SS:PICTURE:AUDIO_UUID",
            }
            audio_uuid = trial_dict.get("audio_uuid")
            if audio_uuid and task_type in audio_uuid_concepts:
                session.add(ObservationFact(
                    ENCOUNTER_NUM=encounter_num,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD=audio_uuid_concepts[task_type],
                    CATEGORY_CHAR=task_type,
                    VALTYPE_CD="T",
                    TVAL_CHAR=audio_uuid,
                    START_DATE=str(trial_dict.get("processed_at") or now),
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))
                observation_count += 1

            # Audio duration
            audio_duration_concepts = {
                "veggie": "SS:VEGGIE:AUDIO_DURATION",
                "saying": "SS:SAYING:AUDIO_DURATION",
                "picture": "SS:PICTURE:AUDIO_DURATION",
            }
            audio_duration = trial_dict.get("audio_duration_seconds")
            if audio_duration is not None and task_type in audio_duration_concepts:
                session.add(ObservationFact(
                    ENCOUNTER_NUM=encounter_num,
                    PATIENT_NUM=patient_num,
                    CONCEPT_CD=audio_duration_concepts[task_type],
                    CATEGORY_CHAR=task_type,
                    VALTYPE_CD="N",
                    NVAL_NUM=audio_duration,
                    UNIT_CD="s",
                    START_DATE=str(trial_dict.get("processed_at") or now),
                    INSTANCE_NUM=1,
                    SOURCESYSTEM_CD="LEGACY_MIGRATION",
                    IMPORT_DATE=now,
                    UPDATE_DATE=now,
                ))
                observation_count += 1

            # Commit in batches
            if (i + 1) % BATCH_SIZE == 0:
                session.commit()
                logger.info("Committed batch %d (%d trials processed)", (i + 1) // BATCH_SIZE, i + 1)

        # ── Create USER_PATIENT_LOOKUP entries ───────────────
        # We need to resolve usernames to user IDs from the user database
        # For now, use a simple approach: store username hash as user_id
        # The actual user_id resolution happens when the user DB is available
        for old_patient_id, patient_num in patient_num_map.items():
            # Find the created_by for this patient
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT created_by FROM patients WHERE id = :pid"),
                    {"pid": old_patient_id},
                ).fetchone()
            if row and row[0]:
                username = row[0]
                import hashlib
                temp_user_id = int(hashlib.sha256(username.encode()).hexdigest()[:8], 16)
                existing = session.query(UserPatientLookup).filter(
                    UserPatientLookup.USER_ID == temp_user_id,
                    UserPatientLookup.PATIENT_NUM == patient_num,
                ).first()
                if not existing:
                    session.add(UserPatientLookup(
                        USER_ID=temp_user_id,
                        PATIENT_NUM=patient_num,
                        NAME_CHAR=username,
                        UPDATE_DATE=now,
                        IMPORT_DATE=now,
                    ))

        session.commit()
        logger.info(
            "Historical migration complete: %d patients, %d visits, %d observations",
            len(patient_num_map), len(encounter_num_map), observation_count,
        )

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
