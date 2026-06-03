"""
Compatibility layer: reconstruct legacy API response format from star schema.

Converts OBSERVATION_FACT rows (EAV) back to the flat trial/analysis dicts
that the frontend expects, ensuring zero breaking changes in the API contract.
"""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from db.models_star import (
    PatientDimension, VisitDimension, ObservationFact, NoteFact,
)
from db.repositories.observation_repository import (
    METRIC_CONCEPT_MAP, TRANSCRIPT_CONCEPTS, AUDIO_UUID_CONCEPTS, AUDIO_DURATION_CONCEPTS,
)
from db.seeds.concepts import SNOMED_TO_GENDER

logger = logging.getLogger(__name__)


def serialize_patient_for_list(patient: PatientDimension, visit_count: int,
                               exported_visit_count: int = 0) -> dict:
    """Serialize patient for GET /patients list response (legacy-compatible)."""
    gender = SNOMED_TO_GENDER.get(patient.SEX_CD, patient.SEX_CD)

    def _export_status(total: int, exported: int) -> str:
        if total == 0 or exported == 0:
            return "none"
        if exported >= total:
            return "full"
        return "partial"

    return {
        "id": patient.PATIENT_NUM,
        "patient_id": patient.PATIENT_CD,
        "gender": gender,
        "birth_date": str(patient.BIRTH_DATE) if patient.BIRTH_DATE else None,
        "created_at": patient.CREATED_AT,
        "created_by": None,  # derived from USER_PATIENT_LOOKUP if needed
        "analysis_count": visit_count,
        "export_status": _export_status(visit_count, exported_visit_count),
    }


def serialize_visit_for_list(visit: VisitDimension, observations: list[ObservationFact],
                              trial_count: int) -> dict:
    """Serialize visit for GET /patients/{id}/analyses list response."""
    # Extract session-level data from observations
    moca_score = None
    group = None
    session_analysis_id = None

    for obs in observations:
        if obs.CONCEPT_CD == "SS:SESSION:MOCA_SCORE":
            moca_score = int(obs.NVAL_NUM) if obs.NVAL_NUM is not None else None
        elif obs.CONCEPT_CD == "SS:SESSION:GROUP":
            group = obs.TVAL_CHAR
        elif obs.CONCEPT_CD == "SS:SESSION:SESSION_ID":
            session_analysis_id = obs.TVAL_CHAR

    return {
        "id": visit.ENCOUNTER_NUM,
        "date": str(visit.START_DATE) if visit.START_DATE else None,
        "moca_score": moca_score,
        "group": group,
        "session_analysis_id": session_analysis_id,
        "exported_at": None,  # TODO: track export status in star schema
        "created_at": visit.CREATED_AT,
        "trial_count": trial_count,
    }


def serialize_visit_detail(visit: VisitDimension, all_observations: list[ObservationFact],
                            notes: list[NoteFact] = None,
                            patient: PatientDimension = None) -> dict:
    """Serialize visit for GET /analyses/{id} detail response (with trials)."""
    # Separate session-level and task-level observations
    session_obs = []
    task_obs: dict[str, list[ObservationFact]] = {}

    for obs in all_observations:
        if obs.CATEGORY_CHAR == "session":
            session_obs.append(obs)
        elif obs.CATEGORY_CHAR in ("veggie", "saying", "picture"):
            task_obs.setdefault(obs.CATEGORY_CHAR, []).append(obs)

    # Extract session-level fields
    moca_score = None
    group = None
    session_analysis_id = None
    for obs in session_obs:
        if obs.CONCEPT_CD == "SS:SESSION:MOCA_SCORE":
            moca_score = int(obs.NVAL_NUM) if obs.NVAL_NUM is not None else None
        elif obs.CONCEPT_CD == "SS:SESSION:GROUP":
            group = obs.TVAL_CHAR
        elif obs.CONCEPT_CD == "SS:SESSION:SESSION_ID":
            session_analysis_id = obs.TVAL_CHAR

    # Extract notes
    notes_text = None
    if notes:
        notes_text = notes[0].NOTE_TEXT if notes else None

    # Reconstruct trials from task observations
    trials = []
    for task_type in ("veggie", "saying", "picture"):
        observations = task_obs.get(task_type, [])
        if not observations:
            continue
        trial = _observations_to_trial_dict(observations, task_type)
        if trial:
            trial["id"] = observations[0].OBSERVATION_ID  # use first obs ID as trial ID
            trials.append(trial)

    return {
        "id": visit.ENCOUNTER_NUM,
        "patient_id": patient.PATIENT_CD if patient else None,
        "date": str(visit.START_DATE) if visit.START_DATE else None,
        "moca_score": moca_score,
        "group": group,
        "notes": notes_text,
        "session_analysis_id": session_analysis_id,
        "created_at": visit.CREATED_AT,
        "trials": trials,
    }


def _observations_to_trial_dict(observations: list[ObservationFact],
                                  task_type: str) -> dict[str, Any]:
    """Convert EAV observations for one task back to flat trial dict."""
    trial: dict[str, Any] = {
        "task": task_type,
        "processed_at": None,
        "attempt_id": None,
        "transcript": None,
        "audio_duration_seconds": None,
        "total_word_count": None,
        "points": None,
        "audio_uuid": None,
        "metrics": {},
    }

    transcript_cd = TRANSCRIPT_CONCEPTS.get(task_type)
    uuid_cd = AUDIO_UUID_CONCEPTS.get(task_type)
    duration_cd = AUDIO_DURATION_CONCEPTS.get(task_type)

    # Reverse map: CONCEPT_CD → metric_key
    concept_map = METRIC_CONCEPT_MAP.get(task_type, {})
    reverse_map = {v: k for k, v in concept_map.items()}

    for obs in observations:
        cd = obs.CONCEPT_CD

        # Use first observation's date and attempt_id
        if trial["processed_at"] is None and obs.START_DATE:
            trial["processed_at"] = obs.START_DATE
        if trial["attempt_id"] is None and obs.PROVIDER_ID:
            trial["attempt_id"] = obs.PROVIDER_ID

        # Special per-trial fields
        if cd == transcript_cd:
            trial["transcript"] = obs.TVAL_CHAR
            continue
        if cd == uuid_cd:
            trial["audio_uuid"] = obs.TVAL_CHAR
            continue
        if cd == duration_cd:
            trial["audio_duration_seconds"] = _to_number(obs.NVAL_NUM)
            continue

        # Metric fields
        metric_key = reverse_map.get(cd)
        if not metric_key:
            continue

        if obs.VALTYPE_CD == "N":
            value = _to_number(obs.NVAL_NUM)
            trial["metrics"][metric_key] = value
        elif obs.VALTYPE_CD == "T":
            text = obs.TVAL_CHAR
            if text and text.startswith(("[", "{")):
                try:
                    text = json.loads(text)
                except (json.JSONDecodeError, ValueError):
                    pass
            trial["metrics"][metric_key] = text

    # Extract top-level fields from metrics
    trial["points"] = trial["metrics"].get("points") or trial["metrics"].get("pic_points")
    trial["total_word_count"] = trial["metrics"].get("total_word_count")

    return trial


def _to_number(val) -> int | float | None:
    """Convert numeric value, preferring int when possible."""
    if val is None:
        return None
    try:
        f = float(val)
        if f == int(f):
            return int(f)
        return f
    except (ValueError, TypeError):
        return None


def find_audio_uuid_for_trial(db: Session, encounter_num: int,
                               task_type: str) -> str | None:
    """Look up the audio_uuid observation for a specific task in a visit."""
    uuid_cd = AUDIO_UUID_CONCEPTS.get(task_type)
    if not uuid_cd:
        return None
    obs = (db.query(ObservationFact)
           .filter(
               ObservationFact.ENCOUNTER_NUM == encounter_num,
               ObservationFact.CONCEPT_CD == uuid_cd,
           )
           .first())
    return obs.TVAL_CHAR if obs else None


def find_audio_uuid_by_observation_id(db: Session, observation_id: int) -> tuple[str | None, int | None]:
    """Find audio_uuid given any observation_id. Returns (audio_uuid, patient_num)."""
    obs = db.query(ObservationFact).filter(
        ObservationFact.OBSERVATION_ID == observation_id
    ).first()
    if not obs:
        return None, None

    task_type = obs.CATEGORY_CHAR
    uuid_cd = AUDIO_UUID_CONCEPTS.get(task_type)
    if not uuid_cd:
        return None, obs.PATIENT_NUM

    uuid_obs = (db.query(ObservationFact)
                .filter(
                    ObservationFact.ENCOUNTER_NUM == obs.ENCOUNTER_NUM,
                    ObservationFact.CONCEPT_CD == uuid_cd,
                    ObservationFact.INSTANCE_NUM == obs.INSTANCE_NUM,
                )
                .first())
    return (uuid_obs.TVAL_CHAR if uuid_obs else None), obs.PATIENT_NUM
