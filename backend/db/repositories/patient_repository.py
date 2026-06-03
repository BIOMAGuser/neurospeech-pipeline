"""Repository for PATIENT_DIMENSION with access control and search."""

import logging
from datetime import datetime

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from ..models_star import PatientDimension, VisitDimension, UserPatientLookup, ObservationFact
from .base import BaseRepository

logger = logging.getLogger(__name__)


class PatientRepository(BaseRepository[PatientDimension]):

    def __init__(self, session: Session):
        super().__init__(session, PatientDimension, "PATIENT_NUM")

    def find_by_code(self, patient_cd: str) -> PatientDimension | None:
        return (self.session.query(PatientDimension)
                .filter(PatientDimension.PATIENT_CD == patient_cd)
                .first())

    def get_or_create(self, patient_cd: str, **kwargs) -> tuple[PatientDimension, bool]:
        """Get existing patient by code or create new. Returns (patient, created)."""
        existing = self.find_by_code(patient_cd)
        if existing:
            return existing, False

        now = datetime.now().isoformat()
        data = {
            "PATIENT_CD": patient_cd,
            "IMPORT_DATE": now,
            "UPDATE_DATE": now,
            "SOURCESYSTEM_CD": kwargs.get("sourcesystem", "SYSTEM"),
            **{k: v for k, v in kwargs.items() if hasattr(PatientDimension, k)},
        }
        patient = self.create(data)
        return patient, True

    def search(self, search_term: str, user_id: int = None,
               is_admin: bool = False, limit: int = 500) -> list[PatientDimension]:
        """Search patients by PATIENT_CD or PATIENT_BLOB content."""
        q = self.session.query(PatientDimension)

        if not is_admin and user_id is not None:
            q = q.join(UserPatientLookup,
                       UserPatientLookup.PATIENT_NUM == PatientDimension.PATIENT_NUM)
            q = q.filter(or_(
                UserPatientLookup.USER_ID == user_id,
                UserPatientLookup.USER_ID == 0,  # public access
            ))

        if search_term:
            pattern = f"%{search_term}%"
            q = q.filter(or_(
                PatientDimension.PATIENT_CD.ilike(pattern),
                PatientDimension.STATECITYZIP_PATH.ilike(pattern),
            ))

        return q.limit(limit).all()

    def get_patients_with_visit_counts(self, user_id: int = None,
                                       is_admin: bool = False,
                                       limit: int = 500, offset: int = 0) -> list[dict]:
        """List patients with analysis (visit) counts and export status."""
        q = (self.session.query(
                PatientDimension,
                func.count(func.distinct(VisitDimension.ENCOUNTER_NUM)).label("visit_count"),
            )
            .outerjoin(VisitDimension,
                       VisitDimension.PATIENT_NUM == PatientDimension.PATIENT_NUM)
            .group_by(PatientDimension.PATIENT_NUM))

        if not is_admin and user_id is not None:
            q = q.join(UserPatientLookup,
                       UserPatientLookup.PATIENT_NUM == PatientDimension.PATIENT_NUM)
            q = q.filter(or_(
                UserPatientLookup.USER_ID == user_id,
                UserPatientLookup.USER_ID == 0,
            ))

        q = q.order_by(PatientDimension.PATIENT_NUM.desc())
        rows = q.offset(offset).limit(limit).all()

        return [
            {
                "patient": patient,
                "visit_count": visit_count,
            }
            for patient, visit_count in rows
        ]

    def ensure_user_access(self, patient_num: int, user_id: int):
        """Create USER_PATIENT_LOOKUP entry if it doesn't exist."""
        existing = (self.session.query(UserPatientLookup)
                    .filter(UserPatientLookup.PATIENT_NUM == patient_num,
                            UserPatientLookup.USER_ID == user_id)
                    .first())
        if not existing:
            lookup = UserPatientLookup(
                USER_ID=user_id,
                PATIENT_NUM=patient_num,
                UPDATE_DATE=datetime.now().isoformat(),
            )
            self.session.add(lookup)
            self.session.flush()

    def check_access(self, patient_num: int, user_id: int, is_admin: bool) -> bool:
        """Check if user has access to patient."""
        if is_admin:
            return True
        return (self.session.query(UserPatientLookup)
                .filter(UserPatientLookup.PATIENT_NUM == patient_num,
                        or_(UserPatientLookup.USER_ID == user_id,
                            UserPatientLookup.USER_ID == 0))
                .first()) is not None
