"""Repository for VISIT_DIMENSION (maps to the old 'analyses' concept)."""

import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..models_star import VisitDimension, ObservationFact, NoteFact, PatientDimension
from .base import BaseRepository

logger = logging.getLogger(__name__)


class VisitRepository(BaseRepository[VisitDimension]):

    def __init__(self, session: Session):
        super().__init__(session, VisitDimension, "ENCOUNTER_NUM")

    def find_by_patient(self, patient_num: int,
                        order_by: str = "START_DATE",
                        order_direction: str = "DESC") -> list[VisitDimension]:
        q = self.session.query(VisitDimension).filter(
            VisitDimension.PATIENT_NUM == patient_num
        )
        if order_by and hasattr(VisitDimension, order_by):
            from sqlalchemy import asc, desc
            col = getattr(VisitDimension, order_by)
            q = q.order_by(desc(col) if order_direction.upper() == "DESC" else asc(col))
        return q.all()

    def find_by_session_id(self, session_analysis_id: str) -> VisitDimension | None:
        """Find visit by session_analysis_id stored in VISIT_BLOB."""
        return (self.session.query(VisitDimension)
                .join(ObservationFact,
                      ObservationFact.ENCOUNTER_NUM == VisitDimension.ENCOUNTER_NUM)
                .filter(
                    ObservationFact.CONCEPT_CD == "SS:SESSION:SESSION_ID",
                    ObservationFact.TVAL_CHAR == session_analysis_id)
                .first())

    def get_or_create(self, patient_num: int, session_analysis_id: str = None,
                      **kwargs) -> tuple[VisitDimension, bool]:
        """Get existing visit by session_id or create new. Returns (visit, created)."""
        if session_analysis_id:
            existing = self.find_by_session_id(session_analysis_id)
            if existing:
                return existing, False

        now = datetime.now().isoformat()
        data = {
            "PATIENT_NUM": patient_num,
            "ACTIVE_STATUS_CD": "SCTID: 55561003",
            "INOUT_CD": "O",
            "START_DATE": kwargs.get("START_DATE", now),
            "SOURCESYSTEM_CD": kwargs.get("SOURCESYSTEM_CD", "SYSTEM"),
            "IMPORT_DATE": now,
            "UPDATE_DATE": now,
            **{k: v for k, v in kwargs.items() if hasattr(VisitDimension, k)},
        }
        visit = self.create(data)
        return visit, True

    def get_with_observations(self, encounter_num: int) -> VisitDimension | None:
        """Load visit with all observations eagerly loaded."""
        return (self.session.query(VisitDimension)
                .options(joinedload(VisitDimension.observations))
                .filter(VisitDimension.ENCOUNTER_NUM == encounter_num)
                .first())

    def get_visits_with_trial_counts(self, patient_num: int) -> list[dict]:
        """List visits for a patient with observation/trial counts per task."""
        visits = self.find_by_patient(patient_num)
        result = []
        for visit in visits:
            # Count distinct task categories (= number of trials)
            trial_count = (self.session.query(func.count(func.distinct(
                    ObservationFact.CATEGORY_CHAR)))
                .filter(ObservationFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM,
                        ObservationFact.CATEGORY_CHAR.in_(["veggie", "saying", "picture"]))
                .scalar()) or 0
            result.append({
                "visit": visit,
                "trial_count": trial_count,
            })
        return result

    def get_notes(self, encounter_num: int) -> list[NoteFact]:
        """Get all notes for a visit."""
        return (self.session.query(NoteFact)
                .filter(NoteFact.ENCOUNTER_NUM == encounter_num)
                .all())
