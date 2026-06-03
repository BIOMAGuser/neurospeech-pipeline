import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db, get_user_db
from db.models_star import PatientDimension, VisitDimension, ObservationFact
from analysis.analyse_saying import gpt_score
from service.auth_service import get_current_user, User
from service.openai_key_service import get_openai_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["debug"], dependencies=[Depends(get_current_user)])


def _require_debug(user: User | None = None):
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    if user and not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugriff erforderlich")


@router.post("/debug_saying")
async def debug_saying(
    text_input: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    user_db: Session = Depends(get_user_db),
):
    _require_debug(current_user)
    api_key = get_openai_api_key(current_user.username, user_db)
    score = gpt_score(text_input, api_key)
    return {"input_text": text_input, "gpt_score": score}


@router.get("/debug/patients")
async def debug_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_debug(current_user)
    patients = db.query(PatientDimension).all()
    return [{"id": p.PATIENT_NUM, "patient_id": p.PATIENT_CD, "created_at": p.CREATED_AT} for p in patients]


@router.get("/debug/analyses")
async def debug_analyses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_debug(current_user)
    visits = db.query(VisitDimension).all()
    return [{"id": v.ENCOUNTER_NUM, "patient_num": v.PATIENT_NUM,
             "date": v.START_DATE, "location": v.LOCATION_CD} for v in visits]


@router.get("/debug/trials")
async def debug_trials(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_debug(current_user)
    obs = db.query(ObservationFact).filter(
        ObservationFact.CATEGORY_CHAR.in_(["veggie", "saying", "picture"])
    ).all()
    return [{"id": o.OBSERVATION_ID, "encounter_num": o.ENCOUNTER_NUM,
             "concept_cd": o.CONCEPT_CD, "category": o.CATEGORY_CHAR} for o in obs]


@router.get("/debug/patient_analysis_trials")
async def debug_patient_analysis_trials(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_debug(current_user)
    query = text("""
        SELECT * FROM patient_observations_v2
        ORDER BY PATIENT_NUM, ENCOUNTER_NUM, concept_name
    """)
    result = db.execute(query)
    return [dict(row._mapping) for row in result]
