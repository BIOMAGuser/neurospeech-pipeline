import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, text, or_
from sqlalchemy.orm import Session

from db.database import get_db, get_user_db
from db.models_star import PatientDimension, VisitDimension, ObservationFact, UserPatientLookup
from service.observation_builder import username_to_user_id
from service.auth_service import get_current_user, User
from service.openai_key_service import get_openai_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Public endpoint: check if the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "error", "database": "unreachable"}


@router.get("/stats")
def stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return counts of patients, visits (analyses), and task-observations (trials)."""
    if current_user.is_admin:
        patient_count = db.query(func.count(PatientDimension.PATIENT_NUM)).scalar() or 0
        visit_count = db.query(func.count(VisitDimension.ENCOUNTER_NUM)).scalar() or 0
        # Count distinct task categories per visit as "trials"
        trial_count = (
            db.query(func.count(func.distinct(
                ObservationFact.ENCOUNTER_NUM.op("||")("-").op("||")(ObservationFact.CATEGORY_CHAR)
            )))
            .filter(ObservationFact.CATEGORY_CHAR.in_(["veggie", "saying", "picture"]))
            .scalar()
        ) or 0
    else:
        # Get patient IDs accessible to this user
        accessible = (
            db.query(UserPatientLookup.PATIENT_NUM)
            .filter(or_(
                UserPatientLookup.USER_ID == username_to_user_id(current_user.username),
                UserPatientLookup.USER_ID == 0,
            ))
            .subquery()
        )
        patient_count = (
            db.query(func.count(PatientDimension.PATIENT_NUM))
            .filter(PatientDimension.PATIENT_NUM.in_(db.query(accessible.c.PATIENT_NUM)))
            .scalar()
        ) or 0
        visit_count = (
            db.query(func.count(VisitDimension.ENCOUNTER_NUM))
            .filter(VisitDimension.PATIENT_NUM.in_(db.query(accessible.c.PATIENT_NUM)))
            .scalar()
        ) or 0
        trial_count = (
            db.query(func.count(func.distinct(
                ObservationFact.ENCOUNTER_NUM.op("||")("-").op("||")(ObservationFact.CATEGORY_CHAR)
            )))
            .filter(
                ObservationFact.CATEGORY_CHAR.in_(["veggie", "saying", "picture"]),
                ObservationFact.PATIENT_NUM.in_(db.query(accessible.c.PATIENT_NUM)),
            )
            .scalar()
        ) or 0

    return {
        "patients": patient_count,
        "analyses": visit_count,
        "trials": trial_count,
    }


@router.get("/openai-status")
def openai_status(
    _user: User = Depends(get_current_user),
    user_db: Session = Depends(get_user_db),
):
    """Authenticated endpoint: check if the OpenAI API is reachable."""
    try:
        api_key = get_openai_api_key(_user.username, user_db)
    except ValueError as e:
        return {"status": "error", "openai": "unreachable", "reason": str(e)}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=5.0)
        client.models.list()
        return {"status": "ok", "openai": "connected", "reason": None}
    except Exception as e:
        logger.error("OpenAI status check failed: %s", e)
        error_str = str(e)
        if "AuthenticationError" in error_str or "401" in error_str:
            reason = "API-Key ungueltig oder abgelaufen"
        elif "RateLimitError" in error_str or "429" in error_str:
            reason = "Rate-Limit erreicht"
        elif "Connection" in error_str or "Timeout" in error_str:
            reason = "Verbindung fehlgeschlagen (Netzwerk/Timeout)"
        else:
            reason = error_str[:120]
        return {"status": "error", "openai": "unreachable", "reason": reason}
