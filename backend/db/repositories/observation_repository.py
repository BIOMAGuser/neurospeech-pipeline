"""Repository for OBSERVATION_FACT — the central measurement table."""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models_star import ObservationFact, ConceptDimension
from .base import BaseRepository

logger = logging.getLogger(__name__)


# Mapping from legacy metric keys to CONCEPT_CDs per task type
METRIC_CONCEPT_MAP = {
    "veggie": {
        "points": "SS:VEGGIE:POINTS",
        "correct_words": "SS:VEGGIE:CORRECT_WORDS",
        "unrelated_words": "SS:VEGGIE:UNRELATED_WORDS",
        "unrelated_words_list": "SS:VEGGIE:UNRELATED_WORDS_LIST",
        "duplicate_count": "SS:VEGGIE:DUPLICATE_COUNT",
        "total_word_count": "SS:VEGGIE:TOTAL_WORD_COUNT",
        "filler_word_count": "SS:VEGGIE:FILLER_WORD_COUNT",
    },
    "saying": {
        "points": "SS:SAYING:POINTS",
        "filler_word_count": "SS:SAYING:FILLER_WORD_COUNT",
        "total_word_count": "SS:SAYING:TOTAL_WORD_COUNT",
    },
    "picture": {
        "points": "SS:PICTURE:POINTS",
        "pic_points": "SS:PICTURE:POINTS",
        "sentence_count": "SS:PICTURE:SENTENCE_COUNT",
        "verb_count": "SS:PICTURE:VERB_COUNT",
        "noun_count": "SS:PICTURE:NOUN_COUNT",
        "pronoun_count": "SS:PICTURE:PRONOUN_COUNT",
        "adverb_count": "SS:PICTURE:ADVERB_COUNT",
        "adjective_count": "SS:PICTURE:ADJECTIVE_COUNT",
        "verb_ratio": "SS:PICTURE:VERB_RATIO",
        "noun_ratio": "SS:PICTURE:NOUN_RATIO",
        "pronoun_ratio": "SS:PICTURE:PRONOUN_RATIO",
        "adverb_ratio": "SS:PICTURE:ADVERB_RATIO",
        "adjective_ratio": "SS:PICTURE:ADJECTIVE_RATIO",
        "ttr": "SS:PICTURE:TTR",
        "avg_sentence_length": "SS:PICTURE:AVG_SENTENCE_LENGTH",
        "filler_word_count": "SS:PICTURE:FILLER_WORD_COUNT",
        "total_word_count": "SS:PICTURE:TOTAL_WORD_COUNT",
    },
    "voicesample": {},  # Acoustic-only audio: no scoring metrics, just the audio anchor
    "acoustic": {
        "f0_mean_hz": "SS:ACOUSTIC:F0_MEAN_HZ",
        "f0_std_hz": "SS:ACOUSTIC:F0_STD_HZ",
        "f0_min_hz": "SS:ACOUSTIC:F0_MIN_HZ",
        "f0_max_hz": "SS:ACOUSTIC:F0_MAX_HZ",
        "jitter_local": "SS:ACOUSTIC:JITTER_LOCAL",
        "jitter_rap": "SS:ACOUSTIC:JITTER_RAP",
        "jitter_ppq5": "SS:ACOUSTIC:JITTER_PPQ5",
        "shimmer_local": "SS:ACOUSTIC:SHIMMER_LOCAL",
        "shimmer_apq3": "SS:ACOUSTIC:SHIMMER_APQ3",
        "shimmer_apq5": "SS:ACOUSTIC:SHIMMER_APQ5",
        "shimmer_apq11": "SS:ACOUSTIC:SHIMMER_APQ11",
        "hnr_mean_db": "SS:ACOUSTIC:HNR_MEAN_DB",
        "hnr_std_db": "SS:ACOUSTIC:HNR_STD_DB",
        **{f"mfcc_{i}_mean": f"SS:ACOUSTIC:MFCC_{i}_MEAN" for i in range(1, 14)},
        **{f"mfcc_{i}_std": f"SS:ACOUSTIC:MFCC_{i}_STD" for i in range(1, 14)},
    },
}

# Concept codes for common per-trial fields
TRANSCRIPT_CONCEPTS = {
    "veggie": "SS:VEGGIE:TRANSCRIPT",
    "saying": "SS:SAYING:TRANSCRIPT",
    "picture": "SS:PICTURE:TRANSCRIPT",
    "voicesample": "SS:VOICESAMPLE:TRANSCRIPT",
}
AUDIO_UUID_CONCEPTS = {
    "veggie": "SS:VEGGIE:AUDIO_UUID",
    "saying": "SS:SAYING:AUDIO_UUID",
    "picture": "SS:PICTURE:AUDIO_UUID",
    "voicesample": "SS:VOICESAMPLE:AUDIO_UUID",
}
AUDIO_DURATION_CONCEPTS = {
    "veggie": "SS:VEGGIE:AUDIO_DURATION",
    "saying": "SS:SAYING:AUDIO_DURATION",
    "picture": "SS:PICTURE:AUDIO_DURATION",
    "voicesample": "SS:VOICESAMPLE:AUDIO_DURATION",
}


class ObservationRepository(BaseRepository[ObservationFact]):

    def __init__(self, session: Session):
        super().__init__(session, ObservationFact, "OBSERVATION_ID")

    def find_by_encounter(self, encounter_num: int,
                          category: str = None) -> list[ObservationFact]:
        q = self.session.query(ObservationFact).filter(
            ObservationFact.ENCOUNTER_NUM == encounter_num
        )
        if category:
            q = q.filter(ObservationFact.CATEGORY_CHAR == category)
        return q.all()

    def find_by_patient(self, patient_num: int,
                        concept_cd: str = None) -> list[ObservationFact]:
        q = self.session.query(ObservationFact).filter(
            ObservationFact.PATIENT_NUM == patient_num
        )
        if concept_cd:
            q = q.filter(ObservationFact.CONCEPT_CD == concept_cd)
        return q.all()

    def find_by_concept(self, concept_cd: str,
                        patient_num: int = None) -> list[ObservationFact]:
        q = self.session.query(ObservationFact).filter(
            ObservationFact.CONCEPT_CD == concept_cd
        )
        if patient_num is not None:
            q = q.filter(ObservationFact.PATIENT_NUM == patient_num)
        return q.all()

    def bulk_create_from_metrics(
        self,
        encounter_num: int,
        patient_num: int,
        task_type: str,
        metrics: dict[str, Any],
        transcript: str = None,
        audio_uuid: str = None,
        audio_duration: float = None,
        attempt_id: str = None,
        provider_id: str = None,
        instance_num: int = 1,
    ) -> list[ObservationFact]:
        """
        Create OBSERVATION_FACT rows from a metrics dict (one row per metric).

        This is the core EAV transformation: each metric key/value becomes
        a separate observation row with the appropriate CONCEPT_CD.
        """
        now = datetime.now().isoformat()
        created = []

        def _add_obs(concept_cd: str, valtype: str, nval=None, tval=None, unit=None):
            obs = ObservationFact(
                ENCOUNTER_NUM=encounter_num,
                PATIENT_NUM=patient_num,
                CONCEPT_CD=concept_cd,
                CATEGORY_CHAR=task_type,
                PROVIDER_ID=provider_id,
                START_DATE=now,
                INSTANCE_NUM=instance_num,
                VALTYPE_CD=valtype,
                NVAL_NUM=nval,
                TVAL_CHAR=tval,
                UNIT_CD=unit,
                SOURCESYSTEM_CD="SYSTEM",
                IMPORT_DATE=now,
                UPDATE_DATE=now,
            )
            self.session.add(obs)
            created.append(obs)

        # Map metrics to observations
        concept_map = METRIC_CONCEPT_MAP.get(task_type, {})
        for metric_key, value in metrics.items():
            if value is None:
                continue
            concept_cd = concept_map.get(metric_key)
            if not concept_cd:
                logger.debug("No concept mapping for %s.%s, skipping", task_type, metric_key)
                continue

            if isinstance(value, (list, dict)):
                _add_obs(concept_cd, "T", tval=json.dumps(value, ensure_ascii=False))
            elif isinstance(value, (int, float)):
                _add_obs(concept_cd, "N", nval=value)
            elif isinstance(value, str):
                _add_obs(concept_cd, "T", tval=value)
            elif isinstance(value, bool):
                _add_obs(concept_cd, "N", nval=1 if value else 0)

        # Transcript
        if transcript is not None:
            transcript_cd = TRANSCRIPT_CONCEPTS.get(task_type)
            if transcript_cd:
                _add_obs(transcript_cd, "T", tval=transcript)

        # Audio UUID
        if audio_uuid is not None:
            uuid_cd = AUDIO_UUID_CONCEPTS.get(task_type)
            if uuid_cd:
                _add_obs(uuid_cd, "T", tval=audio_uuid)

        # Audio duration
        if audio_duration is not None:
            duration_cd = AUDIO_DURATION_CONCEPTS.get(task_type)
            if duration_cd:
                _add_obs(duration_cd, "N", nval=audio_duration, unit="s")

        # Store attempt_id in PROVIDER_ID of all created observations
        if attempt_id:
            for obs in created:
                obs.PROVIDER_ID = attempt_id

        self.session.flush()
        return created

    def reconstruct_trial(self, encounter_num: int, task_type: str,
                          instance_num: int = 1) -> dict[str, Any] | None:
        """
        Reconstruct a legacy trial dict from EAV observations.

        Returns a dict compatible with the old API response format:
        {task, transcript, audio_uuid, audio_duration_seconds, total_word_count,
         points, metrics: {...}}
        """
        observations = (
            self.session.query(ObservationFact)
            .filter(
                ObservationFact.ENCOUNTER_NUM == encounter_num,
                ObservationFact.CATEGORY_CHAR == task_type,
                ObservationFact.INSTANCE_NUM == instance_num,
            )
            .all()
        )
        if not observations:
            return None

        trial = {
            "task": task_type,
            "transcript": None,
            "audio_uuid": None,
            "audio_duration_seconds": None,
            "total_word_count": None,
            "points": None,
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

            # Handle special per-trial fields
            if cd == transcript_cd:
                trial["transcript"] = obs.TVAL_CHAR
                continue
            if cd == uuid_cd:
                trial["audio_uuid"] = obs.TVAL_CHAR
                continue
            if cd == duration_cd:
                trial["audio_duration_seconds"] = obs.NVAL_NUM
                continue

            # Map to metric key
            metric_key = reverse_map.get(cd)
            if not metric_key:
                continue

            if obs.VALTYPE_CD == "N":
                value = obs.NVAL_NUM
                if value is not None and float(value) == int(value):
                    value = int(value)
                trial["metrics"][metric_key] = value
            elif obs.VALTYPE_CD == "T":
                text = obs.TVAL_CHAR
                # Try to parse JSON arrays/objects
                if text and text.startswith(("[", "{")):
                    try:
                        text = json.loads(text)
                    except (json.JSONDecodeError, ValueError):
                        pass
                trial["metrics"][metric_key] = text

        # Extract commonly-used top-level fields from metrics
        trial["points"] = trial["metrics"].get("points") or trial["metrics"].get("pic_points")
        trial["total_word_count"] = trial["metrics"].get("total_word_count")

        return trial

    def get_task_types_for_encounter(self, encounter_num: int) -> list[str]:
        """Get distinct task categories for a visit."""
        rows = (
            self.session.query(func.distinct(ObservationFact.CATEGORY_CHAR))
            .filter(
                ObservationFact.ENCOUNTER_NUM == encounter_num,
                ObservationFact.CATEGORY_CHAR.in_(["veggie", "saying", "picture"]),
            )
            .all()
        )
        return [row[0] for row in rows]

    def get_statistics(self) -> dict:
        """Get observation statistics."""
        total = self.session.query(func.count(ObservationFact.OBSERVATION_ID)).scalar() or 0
        by_category = (
            self.session.query(
                ObservationFact.CATEGORY_CHAR,
                func.count(ObservationFact.OBSERVATION_ID),
            )
            .group_by(ObservationFact.CATEGORY_CHAR)
            .all()
        )
        return {
            "totalObservations": total,
            "byCategory": {cat: count for cat, count in by_category},
        }
